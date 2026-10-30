"""Synthetic trust, endpoint, secret-handle, and modern caller-auth boundary."""
from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import urlsplit

class TrustError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail); self.code, self.detail = code, detail

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
    required = ("fingerprint", "issuer", "notBefore", "notAfter", "san", "keyUsage", "chainValid", "revocation")
    if any(k not in cert for k in required): raise TrustError("certificate_incomplete", "Certificate facts are incomplete.")
    if not cert["chainValid"]: raise TrustError("invalid_chain", "Certificate chain is not valid to a configured anchor.")
    if cert["issuer"] not in profile.issuers: raise TrustError("unknown_ca", "Certificate issuer is not allowed.")
    now = now or datetime.now(timezone.utc)
    if _time(cert["notBefore"]) > now or _time(cert["notAfter"]) < now: raise TrustError("certificate_expired", "Certificate is outside its validity window.")
    if cert["revocation"] != "good": raise TrustError("certificate_revoked", "Certificate revocation status is not good.")
    if hostname not in profile.hostnames or hostname not in cert["san"]: raise TrustError("wrong_hostname", "Hostname is not allowed by profile and certificate SAN.")
    if set(profile.required_key_usage) - set(cert["keyUsage"]): raise TrustError("wrong_key_usage", "Certificate key usage is insufficient.")
    return {"status": "valid", "fingerprint": cert["fingerprint"], "profile": profile.name, "version": profile.version, "hostname": hostname}

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
