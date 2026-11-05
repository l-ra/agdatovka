"""Synthetic trust, endpoint, secret-handle, and modern caller-auth boundary."""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import re
import secrets
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from urllib.parse import urlsplit

class TrustError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail); self.code, self.detail = code, detail


SYNTHETIC_REFERENCE_NOW = datetime(2026, 11, 4, tzinfo=timezone.utc)


def _isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def synthetic_client_certificate(now: datetime) -> dict[str, Any]:
    """Build a CI-only client certificate fixture around an explicit clock."""
    return {
        "fingerprint": "sha256:" + "b" * 64,
        "anchorFingerprint": "sha256:" + "a" * 64,
        "issuer": "Synthetic Test CA",
        "notBefore": _isoformat(now - timedelta(days=1)),
        "notAfter": _isoformat(now + timedelta(days=365)),
        "san": ["isds.synthetic.test"],
        "keyUsage": ["digitalSignature", "keyEncipherment"],
        "chainValid": True,
        "revocation": "good",
    }


def synthetic_application_auth(*, box_id: str, nonce: str, now: datetime) -> dict[str, str]:
    """Build CI-only application authentication valid for the supplied clock."""
    return {
        "boxId": box_id,
        "application": "isds-soap",
        "nonce": nonce,
        "issuedAt": _isoformat(now - timedelta(minutes=1)),
        "expiresAt": _isoformat(now + timedelta(minutes=59)),
    }

def _time(value: str) -> datetime:
    try: return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError) as exc: raise TrustError("invalid_certificate", "Invalid certificate timestamp.") from exc

@dataclass(frozen=True)
class TrustProfile:
    name: str; version: str; anchors: tuple[str, ...]; issuers: tuple[str, ...]; hostnames: tuple[str, ...]
    required_key_usage: tuple[str, ...] = ("digitalSignature", "keyEncipherment"); revocation: str = "required"
    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TrustProfile":
        anchors, issuers, hosts = tuple(value.get("anchorFingerprints", ())), tuple(value.get("allowedIssuers", ())), tuple(value.get("hostnames", ()))
        if not value.get("name") or not value.get("version") or not anchors or not hosts: raise TrustError("invalid_trust_profile", "name, version, anchorFingerprints, and hostnames are required.")
        if any(not re.fullmatch(r"sha256:[0-9a-f]{64}", item) for item in anchors): raise TrustError("invalid_trust_profile", "Trust anchors must be sha256 fingerprints.")
        revocation = value.get("revocation", "required")
        if revocation not in {"required", "best-effort", "disabled"}: raise TrustError("invalid_trust_profile", "Unsupported revocation policy.")
        return cls(str(value["name"]), str(value["version"]), anchors, issuers, hosts, tuple(value.get("requiredKeyUsage", cls.required_key_usage)), str(revocation))

def validate_certificate(cert: Mapping[str, Any], profile: TrustProfile, *, hostname: str, now: datetime | None = None) -> dict[str, Any]:
    required = ("fingerprint", "anchorFingerprint", "issuer", "notBefore", "notAfter", "san", "keyUsage", "chainValid", "revocation")
    if any(k not in cert for k in required): raise TrustError("certificate_incomplete", "Certificate facts are incomplete.")
    if not cert["chainValid"]: raise TrustError("invalid_chain", "Certificate chain is not valid to a configured anchor.")
    anchor = cert["anchorFingerprint"]
    if anchor not in profile.anchors: raise TrustError("untrusted_anchor", "Certificate chain terminates at an unconfigured trust anchor.")
    if cert["issuer"] not in profile.issuers: raise TrustError("unknown_ca", "Certificate issuer is not allowed.")
    now = now or datetime.now(timezone.utc)
    if _time(cert["notBefore"]) > now or _time(cert["notAfter"]) < now: raise TrustError("certificate_expired", "Certificate is outside its validity window.")
    if cert["revocation"] != "good": raise TrustError("certificate_revoked", "Certificate revocation status is not good.")
    if hostname not in profile.hostnames or hostname not in cert["san"]: raise TrustError("wrong_hostname", "Hostname is not allowed by profile and certificate SAN.")
    if set(profile.required_key_usage) - set(cert["keyUsage"]): raise TrustError("wrong_key_usage", "Certificate key usage is insufficient.")
    return {"status": "valid", "fingerprint": cert["fingerprint"], "profile": profile.name, "version": profile.version, "hostname": hostname}


def validate_mtls_identity(
    cert: Mapping[str, Any],
    profile: TrustProfile,
    *,
    hostname: str,
    box_id: str,
    bindings: Mapping[str, Any],
    application: str = "isds-soap",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate the synthetic mTLS peer and its server-side box binding.

    ``bindings`` is deliberately supplied by the caller's policy store, never
    by the wire request. Values may be a fingerprint or a mapping containing
    ``fingerprint``/``application``/``status``. Private keys are not accepted.
    """
    certificate = validate_certificate(cert, profile, hostname=hostname, now=now)
    binding = bindings.get(box_id)
    if isinstance(binding, str):
        expected_fingerprint, expected_application, state = binding, application, "active"
    elif isinstance(binding, Mapping):
        expected_fingerprint = binding.get("fingerprint")
        expected_application = binding.get("application", application)
        state = binding.get("state", "active")
    else:
        raise TrustError("identity_binding_failed", "No certificate binding exists for the requested box.")
    if state not in {"active", "overlap"} or expected_application != application:
        raise TrustError("identity_binding_failed", "The certificate binding is not active for this application.")
    if certificate["fingerprint"] != expected_fingerprint:
        raise TrustError("identity_binding_failed", "The client certificate is not bound to the requested box.")
    return {**certificate, "boxId": box_id, "application": application, "bindingState": state}


def validate_isds_auth(
    auth: Mapping[str, Any],
    *,
    box_id: str,
    application: str = "isds-soap",
    used_nonces: set[str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate synthetic SOAP application authentication, including replay.

    The nonce store is owned by the caller and must be durable/atomic in a
    deployed verifier. This helper consumes a nonce only after all checks pass.
    """
    required = ("boxId", "application", "nonce", "issuedAt", "expiresAt")
    if any(key not in auth for key in required):
        raise TrustError("invalid_application_auth", "Application authentication fields are incomplete.")
    if auth["boxId"] != box_id or auth["application"] != application:
        raise TrustError("identity_binding_failed", "Application authentication is not bound to this box or application.")
    nonce = auth["nonce"]
    if not isinstance(nonce, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", nonce):
        raise TrustError("invalid_application_auth", "Application authentication nonce is invalid.")
    now = now or datetime.now(timezone.utc)
    issued, expires = _time(auth["issuedAt"]), _time(auth["expiresAt"])
    if issued > now or expires <= now or expires <= issued:
        raise TrustError("expired_application_auth", "Application authentication is outside its validity window.")
    if used_nonces is not None and nonce in used_nonces:
        raise TrustError("replayed_application_auth", "Application authentication nonce has already been used.")
    if used_nonces is not None:
        used_nonces.add(nonce)
    return {"status": "authenticated", "boxId": box_id, "application": application, "nonce": nonce,
            "issuedAt": issued.isoformat(), "expiresAt": expires.isoformat()}


def synthetic_nonce() -> str:
    """Generate a CI-safe nonce; this is not a credential or private key."""
    return secrets.token_urlsafe(24)


def unauthorized_soap_fault(code: str = "authentication_failed") -> bytes:
    """Return a stable, wire-safe SOAP fault without trust or credential detail."""
    safe_code = code if re.fullmatch(r"[a-z0-9_]{1,64}", code) else "authentication_failed"
    envelope = ET.Element("{http://schemas.xmlsoap.org/soap/envelope/}Envelope")
    body = ET.SubElement(envelope, "{http://schemas.xmlsoap.org/soap/envelope/}Body")
    fault = ET.SubElement(body, "{http://schemas.xmlsoap.org/soap/envelope/}Fault")
    ET.SubElement(fault, "faultcode").text = "Client.Authentication"
    ET.SubElement(fault, "faultstring").text = "Authentication failed"
    detail = ET.SubElement(fault, "detail")
    ET.SubElement(detail, "code").text = safe_code
    return ET.tostring(envelope, encoding="utf-8", xml_declaration=True)

def validate_endpoint(value: Mapping[str, Any]) -> dict[str, Any]:
    scheme, host, allow = value.get("scheme"), value.get("hostname"), value.get("allowList", [])
    if scheme != "https" or not host or host not in allow: raise TrustError("endpoint_not_allowed", "Only explicitly allow-listed HTTPS endpoints are accepted.")
    parsed = urlsplit(f"{scheme}://{host}")
    if parsed.hostname != host or parsed.username or parsed.password or parsed.port not in (None, 443): raise TrustError("endpoint_not_allowed", "Endpoint contains credentials or an unsafe port.")
    return {"scheme": scheme, "hostname": host, "allowList": list(dict.fromkeys(allow))}

def secret_handle(value: Mapping[str, Any]) -> dict[str, Any]:
    handle = value.get("handle")
    if not isinstance(handle, str) or not re.fullmatch(r"(?:vault|hsm|kms):[A-Za-z0-9._:/-]{3,200}", handle) or any(x in handle.lower() for x in ("private", "begin", "password", "secret")):
        raise TrustError("invalid_secret_handle", "A key must reference a secret-store handle, never key material.")
    return {"handle": handle, "state": value.get("state", "active"), "version": str(value.get("version", "1"))}

def modern_subject(token: str, now: datetime | None = None) -> tuple[str, str, frozenset[str]]:
    parts = token.split(":", 4)
    if len(parts) != 5 or parts[0] != "oidc" or not parts[1] or not parts[2]: raise TrustError("invalid_token", "Modern caller authentication requires an OIDC integration token.")
    try: expires = int(parts[3])
    except ValueError as exc: raise TrustError("invalid_token", "Caller token expiry is invalid.") from exc
    if expires <= int((now or datetime.now(timezone.utc)).timestamp()): raise TrustError("expired_token", "Caller token has expired.")
    return parts[1], parts[2], frozenset(p for p in parts[4].split(",") if p)


def _unb64url(value: str) -> bytes:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise TrustError("invalid_token", "Signed caller token encoding is invalid.")
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, base64.binascii.Error) as exc:
        raise TrustError("invalid_token", "Signed caller token encoding is invalid.") from exc


def validate_signed_oidc(
    token: str,
    *,
    signing_keys: Mapping[str, bytes],
    issuer: str,
    audience: str,
    revoked_token_ids: frozenset[str] = frozenset(),
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate a compact HS256 OIDC-shaped token with explicit trust policy."""
    parts = token.split(".")
    if len(parts) != 3:
        raise TrustError("invalid_token", "Modern caller authentication requires a signed compact token.")
    encoded_header, encoded_claims, encoded_signature = parts
    try:
        header = json.loads(_unb64url(encoded_header))
        claims = json.loads(_unb64url(encoded_claims))
        signature = _unb64url(encoded_signature)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrustError("invalid_token", "Signed caller token is not valid JSON.") from exc
    if not isinstance(header, dict) or header.get("alg") != "HS256" or header.get("typ") not in {None, "JWT"}:
        raise TrustError("invalid_token", "Only the configured HS256 caller-token profile is accepted.")
    kid = header.get("kid")
    key = signing_keys.get(kid) if isinstance(kid, str) else None
    if not isinstance(key, bytes) or not key:
        raise TrustError("unknown_key", "Signed caller token key is not configured.")
    signing_input = f"{encoded_header}.{encoded_claims}".encode("ascii")
    expected = hmac.new(key, signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise TrustError("invalid_signature", "Signed caller token signature is invalid.")
    if not isinstance(claims, dict):
        raise TrustError("invalid_token", "Signed caller token claims are invalid.")
    if claims.get("iss") != issuer:
        raise TrustError("invalid_issuer", "Signed caller token issuer is not allowed.")
    token_audience = claims.get("aud")
    if token_audience != audience and not (isinstance(token_audience, list) and audience in token_audience):
        raise TrustError("invalid_audience", "Signed caller token audience is not allowed.")
    subject, tenant, token_id = claims.get("sub"), claims.get("tenant"), claims.get("jti")
    if not all(isinstance(value, str) and value for value in (subject, tenant, token_id)):
        raise TrustError("invalid_claims", "Signed caller token requires subject, tenant, and token id claims.")
    try:
        expires = int(claims["exp"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TrustError("invalid_claims", "Signed caller token expiry is invalid.") from exc
    if expires <= int((now or datetime.now(timezone.utc)).timestamp()):
        raise TrustError("expired_token", "Caller token has expired.")
    if token_id in revoked_token_ids:
        raise TrustError("revoked_token", "Caller token has been revoked.")
    return {"subject": subject, "tenant": tenant, "tokenId": token_id, "permissions": tuple(claims.get("permissions", ())), "claims": claims}
