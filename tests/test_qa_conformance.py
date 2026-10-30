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
        status, _, _ = self.call("POST", f"/api/v1/messages/{message['id']}/attachments", {"filename": "large.bin", "byteLength": MAX_UPLOAD_BYTES, "contentDigest": "sha256:" + "a" * 64}, key="large"); self.assertEqual(status, 201)
        status, _, problem = self.call("POST", f"/api/v1/messages/{message['id']}/attachments", {"filename": "too-large.bin", "byteLength": MAX_UPLOAD_BYTES + 1, "contentDigest": "sha256:" + "b" * 64}, key="over")
        self.assertEqual((status, problem["code"]), (413, "content_too_large"))

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
