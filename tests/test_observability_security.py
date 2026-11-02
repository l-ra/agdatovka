import json
import unittest

from ag_datovka.app import create_app
from ag_datovka.observability import AuditLedger, RequestContext, Telemetry, TraceSampler, alert_conditions, redact


class ObservabilitySecurityTest(unittest.TestCase):
    def test_context_and_redaction_never_emit_sensitive_fields(self):
        context = RequestContext.create("req-test", "corr-test", "op-test")
        telemetry = Telemetry(sampler=TraceSampler(1.0))
        record = telemetry.emit("request.completed", context, authorization="Bearer synthetic-token", content="private message", status=200, tenantId="tenant-a")
        encoded = json.dumps(record)
        self.assertNotIn("synthetic-token", encoded)
        self.assertNotIn("private message", encoded)
        self.assertEqual(record["requestId"], "req-test")
        self.assertEqual(record["tenantId"], "tenant-a")
        self.assertEqual(redact({"privateKey": "-----BEGIN PRIVATE KEY-----"})["privateKey"], "[REDACTED]")

    def test_sampling_keeps_faults_and_is_deterministic_for_success(self):
        sampler = TraceSampler(0.0)
        self.assertFalse(sampler.include("success-trace"))
        self.assertTrue(sampler.include("failed-trace", outcome="error"))
        self.assertEqual(sampler.include("same-trace"), sampler.include("same-trace"))

    def test_metrics_latency_worker_and_alerts(self):
        telemetry = Telemetry(sampler=TraceSampler(1.0))
        telemetry.worker_result(status="dead_letter", attempts=3, latency_ms=12.5)
        telemetry.count("queue_dead_lettered")
        telemetry.count("backpressure_rejected")
        snapshot = telemetry.snapshot()
        self.assertEqual(snapshot["counters"]["worker_dead_letter"], 1)
        self.assertEqual(snapshot["latencyMs"]["worker_latency_ms"], [12.5])
        self.assertEqual(alert_conditions(snapshot), ["dead_letter_rate", "backpressure"])

    def test_audit_tamper_is_detected_and_rebuild_is_valid(self):
        ledger = AuditLedger()
        ledger.append({"event": "denied", "requestId": "req-1", "actor": "subject-a"})
        ledger.append({"event": "accepted", "requestId": "req-2", "actor": "subject-a"})
        self.assertTrue(ledger.verify())
        ledger.events[0]["actor"] = "subject-attacker"
        self.assertFalse(ledger.verify())
        rebuilt = ledger.rebuild()
        self.assertTrue(rebuilt.verify())

    def test_negative_authorization_cannot_cross_tenant_or_manage_global_policy(self):
        app = create_app(":memory:")
        try:
            def call(method, path, body=None, token="dev:platform", key="k"):
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                if method in {"POST", "PUT", "PATCH", "DELETE"}:
                    headers["Idempotency-Key"] = key
                status, _, raw = app.handle_request(method, path, headers, body or {})
                return status, json.loads(raw)

            status, box_a = call("POST", "/api/v1/boxes", {"name": "A"}, key="box-a")
            self.assertEqual(status, 201)
            status, box_b = call("POST", "/api/v1/boxes", {"name": "B"}, key="box-b")
            self.assertEqual(status, 201)
            status, identity = call("POST", f"/api/v1/boxes/{box_a['id']}/identities", {"subject": "alice", "displayName": "Alice"}, key="identity")
            self.assertEqual(status, 201)
            token = f"dev:{box_a['id']}:{identity['id']}"
            status, problem = call("GET", f"/api/v1/boxes/{box_b['id']}", token=token)
            self.assertEqual((status, problem["code"]), (404, "not_found"))
            status, problem = call("POST", "/api/v1/trust-profiles", {"name": "x", "version": "1", "anchorFingerprints": ["sha256:" + "a" * 64], "hostnames": ["isds.synthetic.test"]}, token=token, key="global")
            self.assertEqual((status, problem["code"]), (403, "forbidden"))
        finally:
            app.close()


if __name__ == "__main__":
    unittest.main()
