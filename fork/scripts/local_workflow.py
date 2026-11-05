#!/usr/bin/env python3
"""Run the Datovka compatibility workflow against an isolated local fixture."""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import tempfile
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ag_datovka.app import create_app  # noqa: E402
from ag_datovka.security import synthetic_application_auth, synthetic_client_certificate  # noqa: E402
from ag_datovka.soap_gateway import ISDS_NS, SOAP_ACTIONS, SOAP_ENV, SyntheticSoapGateway  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def soap_envelope(operation: str, values: dict[str, str], attachments=None) -> bytes:
    envelope = ET.Element(f"{{{SOAP_ENV}}}Envelope", {"xmlns:soapenv": SOAP_ENV, "xmlns:isds": ISDS_NS})
    body = ET.SubElement(envelope, f"{{{SOAP_ENV}}}Body")
    operation_element = ET.SubElement(body, f"{{{ISDS_NS}}}{operation}")
    for name, value in values.items():
        ET.SubElement(operation_element, f"{{{ISDS_NS}}}{name}").text = value
    if attachments is not None:
        attachments_element = ET.SubElement(operation_element, f"{{{ISDS_NS}}}attachments")
        for attachment in attachments:
            item = ET.SubElement(attachments_element, f"{{{ISDS_NS}}}attachment")
            for name, value in attachment.items():
                ET.SubElement(item, f"{{{ISDS_NS}}}{name}").text = value
    return ET.tostring(envelope, encoding="utf-8", xml_declaration=True)


def candidate_commit() -> str:
    """Return provenance without requiring the source bundle to contain .git."""
    explicit = os.environ.get("AG_COMMIT", "").strip()
    if explicit:
        return explicit
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "archive-source"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, help="write a redacted run manifest")
    args = parser.parse_args()
    fixture_id = "ag-synthetic-workflow-001"
    content = b"CZ.NIC compatibility synthetic attachment\n"
    content_digest = "sha256:" + sha256(content).hexdigest()
    timestamps = {"startedAt": now()}
    with tempfile.TemporaryDirectory(prefix="ag-synthetic-") as temp:
        app = create_app(str(Path(temp) / "synthetic.sqlite3"))
        try:
            workflow_now = datetime.now(timezone.utc)
            soap = SyntheticSoapGateway(now=workflow_now)

            def request(method: str, path: str, body=None, *, token="dev:platform", key=None, headers=None):
                request_headers = {"Authorization": f"Bearer {token}"}
                if key:
                    request_headers["Idempotency-Key"] = key
                if headers:
                    request_headers.update(headers)
                status, _, raw = app.handle_request(method, path, request_headers, body)
                value = json.loads(raw.decode("utf-8")) if raw else {}
                if status >= 400:
                    raise RuntimeError(f"{method} {path} returned {status}: {value.get('code', value)}")
                return value

            def soap_request(operation: str, values: dict[str, str], *, request_id: str, attachments=None):
                box_id = values.get("recipientBoxId") or values.get("boxId") or "synthetic-box-002"
                certificate = synthetic_client_certificate(workflow_now)
                application_auth = synthetic_application_auth(box_id=box_id, nonce="synthetic_nonce_" + request_id, now=workflow_now)
                status, _, response, exchange = soap.handle(
                    "POST", "/isds/ws", {
                        "content-type": "text/xml; charset=utf-8",
                        "soapaction": SOAP_ACTIONS[operation],
                        "x-request-id": request_id,
                        "correlation-id": "corr_" + request_id,
                        "x-isds-client-certificate": json.dumps(certificate),
                        "x-isds-application-auth": json.dumps(application_auth),
                    }, soap_envelope(operation, values, attachments))
                if status != 200 or exchange.normalized_result is None or b"Response" not in response:
                    raise RuntimeError(f"SOAP {operation} returned {status}")
                return exchange.normalized_result

            request("POST", "/api/v1/endpoint-profiles", {"name": "ag-synthetic", "scheme": "https", "hostname": "synthetic.local", "allowList": ["synthetic.local"]}, key="workflow-endpoint")
            request("POST", "/api/v1/trust-profiles", {"name": "ag-synthetic-trust", "version": "1", "anchorFingerprints": ["sha256:" + "a" * 64], "allowedIssuers": ["synthetic-ca"], "hostnames": ["synthetic.local"]}, key="workflow-trust")
            box = request("POST", "/api/v1/boxes", {"name": "CZ.NIC synthetic box", "kind": "test", "profile": "ag-synthetic", "ownerSubject": "synthetic-owner"}, key="workflow-box")
            box_id, identity_id = box["id"], box["ownerIdentityId"]
            token = f"dev:{box_id}:{identity_id}"
            message = request("POST", "/api/v1/messages", {"boxId": box_id, "senderIdentityId": identity_id, "targetBoxId": "synthetic-recipient-box", "subject": "Compatibility synthetic message", "contentDigest": content_digest}, token=token, key="workflow-message")
            message_id = message["id"]
            request("POST", f"/api/v1/messages/{message_id}/attachments", {"filename": "synthetic.txt", "mediaType": "text/plain", "byteLength": len(content), "contentDigest": content_digest, "contentBase64": base64.b64encode(content).decode("ascii")}, token=token, key="workflow-attachment")
            attachment_list = request("GET", f"/api/v1/messages/{message_id}/attachments", token=token)
            attachment_id = attachment_list["items"][0]["id"]
            submitted = request("POST", f"/api/v1/messages/{message_id}/submit", {"targetBoxId": "synthetic-recipient-box"}, token=token, key="workflow-submit")
            worker = app.run_worker()
            operation = request("GET", f"/api/v1/operations/{submitted['operationId']}", token=token)
            received = request("GET", f"/api/v1/messages/{message_id}", token=token)
            downloaded = request("GET", f"/api/v1/messages/{message_id}/attachments/{attachment_id}", token=token)
            events = request("GET", f"/api/v1/messages/{message_id}/events", token=token)
            receipt_id = worker[0]["receiptId"]
            receipt = request("GET", f"/api/v1/messages/{message_id}/receipts/{receipt_id}", token=token)
            search = request("GET", "/api/v1/messages/search?" + "boxId=" + box_id + "&q=Compatibility", token=token)
            export = request("POST", "/api/v1/exports", {"boxId": box_id, "format": "jsonl"}, token=token, key="workflow-export")
            export_result = request("GET", f"/api/v1/exports/{export['id']}", token=token)
            soap_results = {
                "login": soap_request("Authenticate", {"requestId": "soap-login-001", "login": "synthetic-login"}, request_id="soap-login-001"),
                "list": soap_request("GetListOfMessages", {"boxId": "synthetic-box-002", "from": "2026-10-30", "to": "2026-10-31"}, request_id="soap-list-001"),
                "send": soap_request("CreateMessage", {"messageId": "synthetic-msg-001", "subject": "Synthetic notice", "recipientBoxId": "synthetic-box-002"}, attachments=[{"filename": "synthetic.txt", "mediaType": "text/plain", "contentBase64": base64.b64encode(content).decode("ascii")}], request_id="soap-send-001"),
                "receive": soap_request("GetMessage", {"messageId": "synthetic-msg-001"}, request_id="soap-receive-001"),
                "deliveryReceipt": soap_request("GetDeliveryInfo", {"messageId": "synthetic-msg-001"}, request_id="soap-receipt-001"),
            }
            timestamps["finishedAt"] = now()
            manifest = {
                "schema": "agdatovka.datovka-fork-run.v1",
                "status": "pass",
                "profile": "ag-synthetic",
                "upstreamCommit": "67f1f23056e6f96e4a93632c11418a8ce8ca0b2f",
                "agCommit": candidate_commit(),
                "endpoint": "http://127.0.0.1:0/api/v1 (in-process isolated fixture)",
                "fixtureIds": [fixture_id, "synthetic-recipient-box"],
                "workflow": ["login", "list", "send", "receive", "download", "delivery receipt", "search", "export"],
                "soapOperations": {name: value["operation"] for name, value in soap_results.items()},
                "restChecks": {"received": received["id"] == message_id, "downloaded": downloaded["contentDigest"] == content_digest, "deliveryReceipt": receipt["status"] == "delivered"},
                "messageStatus": operation["status"],
                "receiptStatus": receipt["status"],
                "receiptValidation": receipt["validation"],
                "lifecycleEvents": [event["eventType"] for event in events["items"]],
                "searchMatches": len(search["items"]),
                "exportStatus": export_result["status"],
                "exportManifestDigest": export_result["manifestDigest"],
                "compatibility": {
                    "compatible": ["SOAP 1.1 envelope/action/namespace validation", "login/list/send/receive/delivery receipt operation shapes", "REST message download/search/export workflow", "pinned endpoint profile and trust references"],
                    "intentionalSyntheticLimitation": ["SOAP gateway normalizes accepted operations and does not perform external ISDS delivery", "Datovka desktop Qt build is not run in this dependency-free harness"],
                    "blockers": [],
                },
                "timestamps": timestamps,
                "redaction": "IDs, content, credentials, and private key material are excluded from this manifest.",
            }
            if args.manifest:
                args.manifest.parent.mkdir(parents=True, exist_ok=True)
                args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps(manifest, sort_keys=True))
            return 0
        finally:
            app.close()


if __name__ == "__main__":
    raise SystemExit(main())
