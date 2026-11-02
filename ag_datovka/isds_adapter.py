"""Offline ISDS compatibility boundary for synthetic protocol payloads."""
from __future__ import annotations

import base64
import hashlib
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Mapping

SOURCE_PROFILE = "isds-reference-2026-06-26"
ADAPTER_VERSION = "ag-isds-adapter-v1"


class AdapterError(ValueError):
    def __init__(self, code: str, detail: str, *, retryable: bool = False) -> None:
        super().__init__(detail)
        self.code, self.detail, self.retryable = code, detail, retryable


@dataclass(frozen=True)
class DomainEvent:
    event_type: str
    message_id: str | None
    source_code: str | None
    source_profile: str
    occurred_at: str | None
    data: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"eventType": self.event_type, "messageId": self.message_id,
                "sourceCode": self.source_code, "sourceProfile": self.source_profile,
                "occurredAt": self.occurred_at, "data": dict(self.data)}


EVENT_MAP = {"EV0": "submitted", "EV2": "delivered", "EV3": "read",
             "EV5": "statutory_fiction", "EV6": "undeliverable",
             "EV8": "delivery_failed", "EV11": "expired"}


def digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class IsdsCompatibilityAdapter:
    """Versioned mapper with no network, credentials, or production data path."""

    def __init__(self, source_profile: str = SOURCE_PROFILE) -> None:
        self.source_profile = source_profile

    def parse_envelope(self, payload: Mapping[str, Any]) -> tuple[DomainEvent, ...]:
        self._require(payload, "messageId", "envelope")
        envelope = payload["envelope"]
        if not isinstance(envelope, Mapping):
            raise AdapterError("invalid_envelope", "envelope must be an object")
        attachments = payload.get("attachments", [])
        if not isinstance(attachments, list) or any(not isinstance(a, Mapping) for a in attachments):
            raise AdapterError("invalid_attachments", "attachments must be a list of objects")
        normalized = []
        for attachment in attachments:
            self._require(attachment, "filename", "mediaType", "contentBase64")
            try:
                raw = base64.b64decode(str(attachment["contentBase64"]), validate=True)
            except (ValueError, TypeError):
                raise AdapterError("invalid_attachment_encoding", "contentBase64 is not valid base64")
            normalized.append({"filename": str(attachment["filename"]), "mediaType": str(attachment["mediaType"]),
                               "byteLength": len(raw), "contentDigest": digest(raw)})
        return (DomainEvent("message_envelope_received", str(payload["messageId"]), None, self.source_profile,
                            payload.get("occurredAt"), {"envelope": dict(envelope), "attachments": normalized}),)

    def parse_large_message(self, payload: Mapping[str, Any]) -> DomainEvent:
        self._require(payload, "messageId", "sizeBytes", "attachmentCount", "endpoint")
        size, count = int(payload["sizeBytes"]), int(payload["attachmentCount"])
        if size < 0 or count < 0:
            raise AdapterError("invalid_large_message", "sizeBytes and attachmentCount must be non-negative")
        if size > 100 * 1024 * 1024 or count > 50:
            raise AdapterError("large_message_limit", "synthetic payload exceeds the pinned VoDZ profile")
        if payload["endpoint"] != "ws2":
            raise AdapterError("invalid_large_message_endpoint", "VoDZ must use the ws2 profile endpoint")
        return DomainEvent("large_message_profile_accepted", str(payload["messageId"]), None, self.source_profile,
                           payload.get("occurredAt"), {"profile": "VoDZ", "endpoint": "ws2", "sizeBytes": size, "attachmentCount": count})

    def parse_auth_response(self, payload: Mapping[str, Any]) -> DomainEvent:
        self._require(payload, "result")
        result = str(payload["result"])
        if result not in {"authenticated", "rejected", "expired"}:
            raise AdapterError("unknown_auth_result", "result is not part of the adapter contract")
        event_type = {"authenticated": "auth_succeeded", "rejected": "auth_rejected", "expired": "auth_expired"}[result]
        return DomainEvent(event_type, None, None, self.source_profile, payload.get("occurredAt"),
                           {"method": payload.get("method", "certificate"), "sessionId": payload.get("sessionId")})

    def parse_event(self, payload: Mapping[str, Any]) -> DomainEvent:
        self._require(payload, "messageId", "eventCode", "occurredAt")
        code = str(payload["eventCode"])
        if code not in EVENT_MAP:
            raise AdapterError("unknown_event_code", f"unsupported ISDS event code: {code}")
        return DomainEvent(EVENT_MAP[code], str(payload["messageId"]), code, self.source_profile,
                           str(payload["occurredAt"]), {"login": payload.get("login"), "reason": payload.get("reason")})

    def parse_receipt(self, raw: bytes, *, format: str = "xml") -> DomainEvent:
        if format not in {"xml", "zfo"}:
            raise AdapterError("unsupported_receipt_format", "receipt format must be xml or zfo")
        occurred_at = None
        validation = {"validator": ADAPTER_VERSION, "signature": "not_present", "chain": "not_present", "error": None}
        try:
            if format == "zfo" and raw.startswith(b"SYNTHETIC-ZFO\n"):
                payload = raw.split(b"\n", 1)[1]
                try:
                    values = json.loads(payload.decode("utf-8"))
                    data = values.get("data", values)
                    message_id, status = values["messageId"], data["status"]
                    validation.update(data.get("validation", {}))
                except (json.JSONDecodeError, KeyError):
                    values = dict(line.split("=", 1) for line in payload.decode().splitlines() if "=" in line)
                    message_id, status = values["messageId"], values["status"]
            else:
                root = ET.fromstring(raw)
                message_id, status = root.attrib["messageId"], root.attrib["status"]
                occurred_at = root.attrib.get("occurredAt")
                validation["signature"] = root.attrib.get("signatureStatus", "not_present")
                validation["chain"] = root.attrib.get("chainStatus", "not_present")
                validation["error"] = root.attrib.get("errorCode")
        except (ET.ParseError, KeyError, UnicodeDecodeError, ValueError, TypeError):
            raise AdapterError("invalid_receipt", "receipt evidence is not valid synthetic XML/ZFO")
        if validation["error"]:
            raise AdapterError("receipt_error", "receipt_error: receipt declares an upstream validation error")
        if validation["signature"] not in {"verified", "not_present"}:
            raise AdapterError("invalid_receipt_signature", "invalid_receipt_signature: receipt signature validation failed")
        if validation["chain"] not in {"verified", "not_present"}:
            raise AdapterError("invalid_receipt_chain", "invalid_receipt_chain: receipt certificate chain validation failed")
        validation["status"] = "passed"
        return DomainEvent("receipt_received", message_id, None, self.source_profile, occurred_at,
                           {"format": format, "status": status, "rawDigest": digest(raw), "rawBytes": len(raw),
                            "rawEvidenceBase64": base64.b64encode(raw).decode("ascii"), "validation": validation, "valid": True})

    def parse_error(self, payload: Mapping[str, Any]) -> DomainEvent:
        self._require(payload, "code", "message")
        return DomainEvent("upstream_error", payload.get("messageId"), str(payload["code"]), self.source_profile,
                           payload.get("occurredAt"), {"retryable": bool(payload.get("retryable", False)), "safeDetail": str(payload["message"])})

    def export_evidence(self, receipt: DomainEvent, *, format: str) -> bytes:
        if receipt.event_type != "receipt_received":
            raise AdapterError("not_receipt", "only receipt events can be exported")
        if format == "xml":
            data = receipt.data
            return (f'<SyntheticReceipt messageId="{receipt.message_id}" status="{data["status"]}" rawDigest="{data["rawDigest"]}" />').encode()
        if format == "zfo":
            return b"SYNTHETIC-ZFO\n" + json.dumps(receipt.as_dict(), sort_keys=True).encode()
        if format == "json":
            return json.dumps(receipt.as_dict(), sort_keys=True).encode()
        raise AdapterError("unsupported_export_format", "supported evidence formats are xml, zfo, and json")

    @staticmethod
    def _require(payload: Mapping[str, Any], *keys: str) -> None:
        missing = [key for key in keys if key not in payload]
        if missing:
            raise AdapterError("missing_field", "missing required field(s): " + ", ".join(missing))
