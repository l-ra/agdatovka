"""Synthetic SOAP 1.1 compatibility boundary.

This module deliberately has no network client, credentials, certificate store,
or production data path.  It validates the public wire shape and maps accepted
requests to the existing offline adapter.  Raw XML, an upstream SOAP fault, and
the normalized result are kept as separate values in :class:`SoapExchange`.
"""
from __future__ import annotations

import base64
import hashlib
import json
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .isds_adapter import MAX_ATTACHMENT_COUNT, AdapterError, IsdsCompatibilityAdapter
from .security import TrustError, TrustProfile, validate_isds_auth, validate_mtls_identity

SOAP_ENV = "http://schemas.xmlsoap.org/soap/envelope/"
ISDS_NS = "http://isds.czechpoint.cz/v20"
XSD_NS = "http://www.w3.org/2001/XMLSchema"
SOAP_ACTIONS = {name: f"urn:isds:{name}" for name in (
    "Authenticate", "CreateMessage", "GetMessage", "GetListOfMessages",
    "GetMessageStateChanges", "GetDeliveryInfo", "GetOwnerInfo", "GetUserInfo",
)}
OPERATIONS = {
    "Authenticate": ("ws", ("requestId", "login")),
    "CreateMessage": ("ws", ("messageId", "subject", "recipientBoxId", "attachments")),
    "GetMessage": ("ws", ("messageId",)),
    "GetListOfMessages": ("ws", ("boxId", "from", "to")),
    "GetMessageStateChanges": ("ws", ("boxId", "from", "to")),
    "GetDeliveryInfo": ("ws", ("messageId",)),
    "GetOwnerInfo": ("ws", ("boxId",)),
    "GetUserInfo": ("ws", ("userId",)),
}


@dataclass(frozen=True)
class SoapExchange:
    raw_xml: bytes
    upstream_fault: bytes | None
    normalized_result: Mapping[str, Any] | None


class SoapFault(ValueError):
    def __init__(self, code: str, reason: str, detail: str, status: int = 400) -> None:
        super().__init__(detail)
        self.code, self.reason, self.detail, self.status = code, reason, detail, status


def _tag(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class SyntheticSoapGateway:
    """Strict, deterministic SOAP 1.1 gateway for synthetic fixtures."""

    def __init__(self, adapter: IsdsCompatibilityAdapter | None = None, *, now: datetime | None = None) -> None:
        self.adapter = adapter or IsdsCompatibilityAdapter()
        self._now = now
        self._used_nonces: set[str] = set()
        self._trust_profile = TrustProfile.from_mapping({
            "name": "synthetic-mtls",
            "version": "2026-10-30",
            "anchorFingerprints": ["sha256:" + "a" * 64],
            "allowedIssuers": ["Synthetic Test CA"],
            "hostnames": ["isds.synthetic.test"],
            "requiredKeyUsage": ["digitalSignature", "keyEncipherment"],
            "revocation": "required",
        })
        self._bindings = {
            "synthetic-box-002": {
                "fingerprint": "sha256:" + "b" * 64,
                "application": "isds-soap",
                "state": "active",
            },
        }

    def handle(self, method: str, path: str, headers: Mapping[str, str], raw_xml: bytes) -> tuple[int, dict[str, str], bytes, SoapExchange]:
        request_id = headers.get("x-request-id") or headers.get("correlation-id") or f"req_{uuid.uuid4().hex}"
        correlation_id = headers.get("correlation-id") or request_id
        try:
            if method.upper() != "POST":
                raise SoapFault("Client.MethodNotAllowed", "Only SOAP POST is supported", "Use HTTP POST with a SOAP 1.1 envelope.", 405)
            expected_endpoint = "ws2" if path.rstrip("/").endswith("/ws2") else "ws" if path.rstrip("/").endswith("/ws") else None
            if expected_endpoint is None:
                raise SoapFault("Client.Endpoint", "Unknown endpoint", "The synthetic SOAP endpoint is /isds/ws or /isds/ws2.", 404)
            if len(raw_xml) > 100 * 1024 * 1024:
                raise SoapFault("Client.MessageTooLarge", "Message too large", "The synthetic SOAP boundary accepts at most 100 MiB.", 413)
            operation, values = self._parse_request(raw_xml, headers)
            profile, required = OPERATIONS[operation]
            if expected_endpoint != profile:
                raise SoapFault("Client.Endpoint", "Operation is not available on this endpoint", f"{operation} requires /isds/{profile}.")
            self._verify_trust(values, headers)
            result = self._normalize(operation, values, request_id, correlation_id)
            response = self._response(operation, result, request_id, correlation_id)
            exchange = SoapExchange(raw_xml, None, result)
            return 200, self._headers(request_id), response, exchange
        except SoapFault as fault:
            response = self._fault(fault, request_id, correlation_id)
            return fault.status, {**self._headers(request_id), "content-type": "text/xml; charset=utf-8"}, response, SoapExchange(raw_xml, response, None)

    def _verify_trust(self, values: Mapping[str, Any], headers: Mapping[str, str]) -> None:
        """Require the ISDS identity; management bearer auth is not accepted here."""
        box_id = values.get("recipientBoxId") or values.get("boxId") or "synthetic-box-002"
        try:
            certificate = json.loads(headers.get("x-isds-client-certificate", ""))
            application_auth = json.loads(headers.get("x-isds-application-auth", ""))
            if not isinstance(certificate, dict) or not isinstance(application_auth, dict):
                raise ValueError
            validate_mtls_identity(
                certificate,
                self._trust_profile,
                hostname="isds.synthetic.test",
                box_id=box_id,
                bindings=self._bindings,
                now=self._now,
            )
            validate_isds_auth(
                application_auth,
                box_id=box_id,
                used_nonces=self._used_nonces,
                now=self._now,
            )
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            raise SoapFault("Client.Authentication", "Authentication failed", "A synthetic certificate and application identity are required.", 401) from error
        except TrustError as error:
            raise SoapFault("Client.Authentication", "Authentication failed", error.detail, 401) from error

    def _parse_request(self, raw: bytes, headers: Mapping[str, str]) -> tuple[str, dict[str, Any]]:
        action = headers.get("soapaction", "").strip().strip('"')
        if not action:
            raise SoapFault("Client.MissingSOAPAction", "Missing SOAPAction", "SOAPAction is required for SOAP 1.1 requests.")
        try:
            root = ET.fromstring(raw)
        except (ET.ParseError, ValueError):
            raise SoapFault("Client.MalformedXML", "Malformed XML", "The request is not well-formed XML.")
        if root.tag != _tag(SOAP_ENV, "Envelope"):
            raise SoapFault("Client.Namespace", "Invalid SOAP namespace", "The document root must be a SOAP 1.1 Envelope.")
        body = root.find(_tag(SOAP_ENV, "Body"))
        if body is None or len(body) != 1:
            raise SoapFault("Client.Sequence", "Invalid SOAP Body", "SOAP Body must contain exactly one operation element.")
        operation_element = body[0]
        operation = _local(operation_element.tag)
        if operation_element.tag != _tag(ISDS_NS, operation) or operation not in OPERATIONS:
            raise SoapFault("Client.UnsupportedOperation", "Unsupported operation", f"{operation} is not in the synthetic public operation surface.")
        expected_action = SOAP_ACTIONS[operation]
        if action != expected_action:
            raise SoapFault("Client.SOAPAction", "SOAPAction does not match operation", f"Expected {expected_action}.")
        values: dict[str, Any] = {}
        expected = OPERATIONS[operation][1]
        children = list(operation_element)
        if [_local(c.tag) for c in children] != list(expected):
            raise SoapFault("Client.Sequence", "Invalid element sequence", f"{operation} requires the sequence: {', '.join(expected)}.")
        for child in children:
            if child.tag != _tag(ISDS_NS, _local(child.tag)):
                raise SoapFault("Client.Namespace", "Invalid element namespace", "All operation elements must use the ISDS namespace.")
            if child.tag.endswith("attachments"):
                attachments = []
                items = list(child)
                if len(items) > MAX_ATTACHMENT_COUNT:
                    raise SoapFault("Client.AttachmentLimit", "Attachment count limit exceeded", "CreateMessage accepts at most 50 attachments.")
                for item in items:
                    if item.tag != _tag(ISDS_NS, "attachment"):
                        raise SoapFault("Client.Namespace", "Invalid attachment namespace", "Attachments must use the ISDS namespace.")
                    fields = { _local(x.tag): x.text or "" for x in list(item) }
                    if list(fields) != ["filename", "mediaType", "contentBase64"]:
                        raise SoapFault("Client.Sequence", "Invalid attachment sequence", "attachment requires filename, mediaType, contentBase64.")
                    attachments.append(fields)
                values["attachments"] = attachments
            else:
                values[_local(child.tag)] = child.text or ""
        return operation, values

    def _normalize(self, operation: str, values: dict[str, Any], request_id: str, correlation_id: str) -> dict[str, Any]:
        if operation == "CreateMessage":
            payload = {"messageId": values["messageId"], "occurredAt": "2026-10-30T00:00:00Z", "envelope": {"recipientBoxId": values["recipientBoxId"], "subject": values["subject"]}, "attachments": values["attachments"]}
            try:
                event = self.adapter.parse_envelope(payload)[0]
            except AdapterError as error:
                raise SoapFault("Client.InvalidMessage", "Invalid message", error.detail)
            return {"operation": operation, "event": event.as_dict(), "requestId": request_id, "correlationId": correlation_id}
        return {"operation": operation, "status": "accepted", "values": values, "requestId": request_id, "correlationId": correlation_id}

    def _response(self, operation: str, result: Mapping[str, Any], request_id: str, correlation_id: str) -> bytes:
        envelope = ET.Element(_tag(SOAP_ENV, "Envelope"), {"xmlns:soapenv": SOAP_ENV, "xmlns:isds": ISDS_NS})
        body = ET.SubElement(envelope, _tag(SOAP_ENV, "Body"))
        response = ET.SubElement(body, _tag(ISDS_NS, operation + "Response"))
        ET.SubElement(response, _tag(ISDS_NS, "requestId")).text = request_id
        ET.SubElement(response, _tag(ISDS_NS, "correlationId")).text = correlation_id
        ET.SubElement(response, _tag(ISDS_NS, "status")).text = str(result.get("status", "accepted"))
        if result.get("event"):
            event = result["event"]
            ET.SubElement(response, _tag(ISDS_NS, "eventType")).text = str(event["eventType"])
            ET.SubElement(response, _tag(ISDS_NS, "sourceProfile")).text = str(event["sourceProfile"])
        return ET.tostring(envelope, encoding="utf-8", xml_declaration=True)

    @staticmethod
    def _headers(request_id: str) -> dict[str, str]:
        return {"content-type": "text/xml; charset=utf-8", "x-request-id": request_id}

    @staticmethod
    def _fault(fault: SoapFault, request_id: str, correlation_id: str) -> bytes:
        envelope = ET.Element(_tag(SOAP_ENV, "Envelope"), {"xmlns:soapenv": SOAP_ENV, "xmlns:isds": ISDS_NS})
        body = ET.SubElement(envelope, _tag(SOAP_ENV, "Body"))
        fault_element = ET.SubElement(body, _tag(SOAP_ENV, "Fault"))
        ET.SubElement(fault_element, "faultcode").text = fault.code
        ET.SubElement(fault_element, "faultstring").text = fault.reason
        detail = ET.SubElement(fault_element, "detail")
        ET.SubElement(detail, _tag(ISDS_NS, "errorCode")).text = fault.code
        ET.SubElement(detail, _tag(ISDS_NS, "message")).text = fault.detail
        ET.SubElement(detail, _tag(ISDS_NS, "requestId")).text = request_id
        ET.SubElement(detail, _tag(ISDS_NS, "correlationId")).text = correlation_id
        return ET.tostring(envelope, encoding="utf-8", xml_declaration=True)
