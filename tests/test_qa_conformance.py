import base64
import hashlib
import io
import json
import unittest
from datetime import date
from pathlib import Path

from ag_datovka import create_app
from ag_datovka.app import MAX_UPLOAD_BYTES
from qa.fixtures import PROFILE, SEED, load_manifest
from qa.metrics import MetricsCollector
from qa.retention import add_reference_days, reference_retention
from qa.scans import scan_fixture_text

ROOT = Path(__file__).parents[1]

class FixtureManifestTest(unittest.TestCase):
    def test_manifest_is_deterministic_and_synthetic(self):
        manifest = load_manifest()
        self.assertEqual((manifest["profile"], manifest["seed"]), (PROFILE, SEED))
        self.assertTrue(manifest["syntheticOnly"])
        self.assertEqual(manifest["endpoint"], "https://synthetic.invalid/ag-v1")
        self.assertEqual(manifest["families"]["lifecycle"][-1]["events"], ["EV0", "EV11"])

    def test_fixture_scan_rejects_real_host_or_secret(self):
        text = (ROOT / "qa" / "fixtures.json").read_text(encoding="utf-8")
        self.assertEqual(scan_fixture_text([text]), [])
        self.assertIn("production-host", scan_fixture_text(["https://datovka.gov.cz/api"]))
        self.assertIn("secret-like-value", scan_fixture_text(['token="not-a-real-secret-value"']))

class RetentionClockTest(unittest.TestCase):
    def test_weekend_and_holiday_are_not_counted(self):
        self.assertEqual(add_reference_days(date(2026, 12, 31), 1, {date(2027, 1, 1)}), date(2027, 1, 4))

    def test_reference_profiles_and_legal_hold(self):
        delivered = date(2026, 1, 2)
        ordinary = reference_retention("ordinary", delivered, date(2026, 5, 11))
        system = reference_retention("system", delivered, date(2026, 6, 26))
        held = reference_retention("ordinary", delivered, date(2027, 1, 1), legal_hold=True)
        self.assertEqual(ordinary.eligible_on, date(2026, 5, 8)); self.assertTrue(ordinary.eligible)
        self.assertEqual(system.eligible_on, date(2026, 5, 22)); self.assertTrue(system.eligible)
        self.assertFalse(held.eligible); self.assertEqual(held.reason, "legal_hold")

class ConformanceBoundaryTest(unittest.TestCase):
    def setUp(self): self.app = create_app(":memory:"); self.n = 0
    def tearDown(self): self.app.close()
    def call(self, method, path, body=None, *, token="dev:platform", key=None):
        self.n += 1; headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if method in {"POST", "PUT", "PATCH", "DELETE"}: headers["Idempotency-Key"] = key or f"qa-{self.n}"
        status, response_headers, raw = self.app.handle_request(method, path, headers, body or {})
        return status, response_headers, json.loads(raw)

    def test_large_boundary_and_negative_upload(self):
        self.assertEqual(MAX_UPLOAD_BYTES, 16 * 1024 * 1024)
        status, _, box = self.call("POST", "/api/v1/boxes", {"name": "QA"}, key="box"); self.assertEqual(status, 201)
        status, _, message = self.call("POST", "/api/v1/messages", {"boxId": box["id"], "subject": "boundary"}, key="message"); self.assertEqual(status, 201)
        content = b"x" * MAX_UPLOAD_BYTES
        encoded = base64.b64encode(content).decode("ascii")
        expected = "sha256:" + hashlib.sha256(content).hexdigest()
        status, _, attachment = self.call("POST", f"/api/v1/messages/{message['id']}/attachments", {"filename": "large.bin", "byteLength": MAX_UPLOAD_BYTES, "contentDigest": expected, "contentBase64": encoded}, key="large"); self.assertEqual(status, 201); self.assertTrue(attachment["verified"])
        status, _, problem = self.call("POST", f"/api/v1/messages/{message['id']}/attachments", {"filename": "too-large.bin", "byteLength": MAX_UPLOAD_BYTES + 1, "contentBase64": "eA=="}, key="over")
        self.assertEqual((status, problem["code"]), (413, "content_too_large"))

    def test_attachment_metadata_is_rejected_and_declared_values_are_verified(self):
        status, _, box = self.call("POST", "/api/v1/boxes", {"name": "Integrity QA"}, key="box"); self.assertEqual(status, 201)
        status, _, message = self.call("POST", "/api/v1/messages", {"boxId": box["id"], "subject": "integrity"}, key="message"); self.assertEqual(status, 201)
        path = f"/api/v1/messages/{message['id']}/attachments"
        status, _, problem = self.call("POST", path, {"filename": "metadata-only.bin", "byteLength": 1, "contentDigest": "sha256:" + "0" * 64}, key="metadata")
        self.assertEqual((status, problem["code"]), (415, "content_bytes_required"))
        status, _, problem = self.call("POST", path, {"filename": "mismatch.bin", "byteLength": 3, "contentDigest": "sha256:" + "0" * 64, "contentBase64": base64.b64encode(b"ok").decode()}, key="mismatch")
        self.assertEqual((status, problem["code"]), (422, "content_length_mismatch"))

    def test_octet_stream_boundary_computes_digest_from_received_bytes(self):
        status, _, box = self.call("POST", "/api/v1/boxes", {"name": "Stream QA"}, key="box"); self.assertEqual(status, 201)
        status, _, message = self.call("POST", "/api/v1/messages", {"boxId": box["id"], "subject": "stream"}, key="message"); self.assertEqual(status, 201)
        headers = {"Authorization": "Bearer dev:platform", "Content-Type": "application/octet-stream", "Idempotency-Key": "stream-attachment", "X-Upload-Filename": "stream.txt", "X-Content-Length": "13"}
        status, _, raw = self.app.handle_request("POST", f"/api/v1/messages/{message['id']}/attachments", headers, b"hello stream!")
        attachment = json.loads(raw)
        self.assertEqual((status, attachment["byteLength"], attachment["contentDigest"], attachment["verified"]), (201, 13, "sha256:e9bf69df89b21d3084b1e2200701c12ba62ae1edac58e6c50bd601360f21ae46", True))

    def test_declared_length_problem_semantics_are_stable(self):
        status, _, box = self.call("POST", "/api/v1/boxes", {"name": "Length QA"}, key="box"); self.assertEqual(status, 201)
        status, _, message = self.call("POST", "/api/v1/messages", {"boxId": box["id"], "subject": "lengths"}, key="message"); self.assertEqual(status, 201)
        path = f"/api/v1/messages/{message['id']}/attachments"
        cases = [(None, 400), ("not-an-integer", 400), (float("nan"), 400), (float("inf"), 400), (-1, 400), (MAX_UPLOAD_BYTES + 1, 413)]
        for number, expected_status in cases:
            payload = {"filename": "length.bin", "byteLength": number, "contentBase64": base64.b64encode(b"x").decode()}
            status, _, problem = self.call("POST", path, payload, key=f"length-{len(str(number))}-{expected_status}")
            if number is None:
                # A missing declaration is valid: the received bytes remain authoritative.
                self.assertEqual(status, 201)
                continue
            self.assertEqual((status, problem["code"], problem["status"]), (expected_status, "invalid_content_length" if expected_status == 400 else "content_too_large", expected_status))

    def test_wsgi_octet_stream_ingress_and_malformed_transport_lengths(self):
        status, _, box = self.call("POST", "/api/v1/boxes", {"name": "WSGI QA"}, key="box"); self.assertEqual(status, 201)
        status, _, message = self.call("POST", "/api/v1/messages", {"boxId": box["id"], "subject": "stream"}, key="message"); self.assertEqual(status, 201)
        content = b"resumable synthetic bytes"
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        captured = {}
        environ = {
            "REQUEST_METHOD": "POST", "PATH_INFO": f"/api/v1/messages/{message['id']}/attachments",
            "CONTENT_TYPE": "application/octet-stream", "CONTENT_LENGTH": str(len(content)),
            "HTTP_AUTHORIZATION": "Bearer dev:platform", "HTTP_IDEMPOTENCY_KEY": "wsgi-upload",
            "HTTP_X_UPLOAD_FILENAME": "stream.bin", "HTTP_X_CONTENT_LENGTH": str(len(content)),
            "HTTP_X_CONTENT_DIGEST": digest, "wsgi.input": io.BytesIO(content),
        }
        raw_response = self.app(environ, lambda status_line, headers: captured.update(status=status_line, headers=dict(headers)))
        attachment = json.loads(b"".join(raw_response))
        self.assertEqual((captured["status"].split()[0], attachment["verified"], attachment["contentDigest"]), ("201", True, digest))

        for malformed in ("not-an-integer", "-1"):
            captured = {}
            bad = {"REQUEST_METHOD": "POST", "PATH_INFO": f"/api/v1/messages/{message['id']}/attachments", "CONTENT_TYPE": "application/octet-stream", "CONTENT_LENGTH": malformed, "HTTP_AUTHORIZATION": "Bearer dev:platform", "wsgi.input": io.BytesIO(b"x")}
            raw_response = self.app(bad, lambda status_line, headers: captured.update(status=status_line, headers=dict(headers)))
            problem = json.loads(b"".join(raw_response))
            self.assertEqual((captured["status"].split()[0], problem["code"], problem["status"]), ("400", "invalid_content_length", 400))

    def test_export_manifest_is_stable(self):
        status, _, box = self.call("POST", "/api/v1/boxes", {"name": "Evidence QA"}, key="box"); self.assertEqual(status, 201)
        status, _, msg = self.call("POST", "/api/v1/messages", {"boxId": box["id"], "subject": "evidence"}, key="message"); self.assertEqual(status, 201)
        status, _, export = self.call("POST", "/api/v1/exports", {"boxId": box["id"], "format": "jsonl"}, key="export"); self.assertEqual(status, 202)
        status, _, fetched = self.call("GET", f"/api/v1/exports/{export['id']}"); self.assertEqual(status, 200)
        self.assertEqual(fetched["manifestDigest"], export["manifestDigest"]); self.assertEqual(fetched["result"]["messages"][0]["id"], msg["id"])

    def test_fault_plan_and_redacted_metrics_shape(self):
        faults = load_manifest()["families"]["faults"]
        retryable = {item["fault"] for item in faults if item["retryable"]}
        self.assertIn("worker_crash_after_side_effect", retryable); self.assertNotIn("queue_poison", retryable)
        metrics = MetricsCollector(); metrics.count("accepted", 2); metrics.observe("api.admission_ms", 12.5)
        snapshot = metrics.snapshot(); self.assertEqual(snapshot["counters"], {"accepted": 2}); self.assertNotIn("content", json.dumps(snapshot))

if __name__ == "__main__": unittest.main()
