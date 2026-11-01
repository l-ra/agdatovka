import json
import base64
import concurrent.futures
import tempfile
import unittest

from ag_datovka import create_app


class ManagementApiTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(":memory:")
        self.key_number = 0

    def tearDown(self):
        self.app.close()

    def call(self, method, path, body=None, *, token="dev:platform", key=None):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            self.key_number += 1
            headers["Idempotency-Key"] = key or f"test-{self.key_number}"
        status, response_headers, raw = self.app.handle_request(method, path, headers, body or {})
        return status, response_headers, json.loads(raw)

    def create_box(self, name="Synthetic box"):
        status, _, data = self.call("POST", "/api/v1/boxes", {"name": name, "kind": "test"})
        self.assertEqual(status, 201)
        return data

    def test_create_box_replay_and_idempotency_conflict(self):
        first_status, first_headers, first = self.call("POST", "/api/v1/boxes", {"name": "Replay box"}, key="box-replay")
        replay_status, replay_headers, replay = self.call("POST", "/api/v1/boxes", {"name": "Replay box"}, key="box-replay")
        conflict_status, _, conflict = self.call("POST", "/api/v1/boxes", {"name": "Different"}, key="box-replay")

        self.assertEqual(first_status, 201)
        self.assertEqual(replay_status, 201)
        self.assertEqual(first["id"], replay["id"])
        self.assertEqual(replay_headers["idempotent-replay"], "true")
        self.assertEqual(conflict_status, 409)
        self.assertEqual(conflict["code"], "idempotency_conflict")

    def test_tenant_isolation_and_denied_policy(self):
        first = self.create_box("Tenant one")
        second = self.create_box("Tenant two")
        identity_status, _, identity = self.call("POST", f"/api/v1/boxes/{first['id']}/identities", {"subject": "operator-1", "displayName": "Operator"}, key="identity-1")
        self.assertEqual(identity_status, 201)
        member_status, _, membership = self.call("PUT", f"/api/v1/boxes/{first['id']}/members/{identity['id']}", {"role": "box-operator"}, key="member-1")
        self.assertEqual(member_status, 200)
        operator_token = f"dev:{first['id']}:{identity['id']}"

        status, _, problem = self.call("GET", f"/api/v1/boxes/{second['id']}", token=operator_token)
        self.assertEqual(status, 404)
        self.assertEqual(problem["code"], "not_found")
        status, _, problem = self.call("POST", "/api/v1/roles", {"name": "attempted"}, token=operator_token, key="role-deny")
        self.assertEqual(status, 403)
        self.assertEqual(problem["code"], "forbidden")

        # The denied action is itself an audit record, while its content is not leaked.
        status, _, audit = self.call("GET", f"/api/v1/audit/events?boxId={first['id']}", token=operator_token)
        self.assertEqual(status, 403)
        self.assertEqual(audit["code"], "forbidden")

    def test_tenant_cannot_mutate_global_policy_or_assign_platform_role(self):
        box = self.create_box("Policy tenant")
        token = f"dev:{box['id']}:{box['ownerIdentityId']}"
        status, _, problem = self.call("POST", "/api/v1/roles", {"name": "tenant-global"}, token=token, key="tenant-role")
        self.assertEqual((status, problem["code"]), (403, "forbidden"))
        status, _, problem = self.call("POST", "/api/v1/permissions", {"code": "tenant-global"}, token=token, key="tenant-permission")
        self.assertEqual((status, problem["code"]), (403, "forbidden"))
        status, _, problem = self.call("POST", "/api/v1/trust-profiles", {"name": "tenant-root", "version": "1", "anchorFingerprints": ["sha256:" + "a" * 64], "hostnames": ["isds.synthetic.test"]}, token=token, key="tenant-trust")
        self.assertEqual((status, problem["code"]), (403, "forbidden"))
        identity_status, _, identity = self.call("POST", f"/api/v1/boxes/{box['id']}/identities", {"subject": "operator"}, token=token, key="tenant-identity")
        self.assertEqual(identity_status, 201)
        status, _, problem = self.call("PUT", f"/api/v1/boxes/{box['id']}/members/{identity['id']}", {"role": "platform-admin"}, token=token, key="tenant-platform-role")
        self.assertEqual((status, problem["code"]), (403, "forbidden"))

    def test_cross_tenant_identity_references_are_rejected(self):
        first = self.create_box("Reference source")
        second = self.create_box("Reference target")
        token = f"dev:{first['id']}:{first['ownerIdentityId']}"
        status, _, problem = self.call("POST", "/api/v1/messages", {"boxId": first["id"], "senderIdentityId": second["ownerIdentityId"], "subject": "must reject"}, token=token, key="cross-tenant-sender")
        self.assertEqual(status, 422)
        self.assertEqual(problem["code"], "cross_tenant_reference")
        status, _, problem = self.call("POST", "/api/v1/auth-methods", {"boxId": first["id"], "identityId": second["ownerIdentityId"], "type": "oidc"}, token=token, key="cross-tenant-auth")
        self.assertEqual(status, 422)
        self.assertEqual(problem["code"], "cross_tenant_reference")

    def test_cursor_pagination_is_bounded_and_stable(self):
        box = self.create_box("Pagination box")
        for number in range(5):
            status, _, _ = self.call("POST", "/api/v1/messages", {"boxId": box["id"], "subject": f"message-{number}"}, key=f"message-{number}")
            self.assertEqual(status, 201)
        status, _, page_one = self.call("GET", f"/api/v1/messages/search?boxId={box['id']}&limit=2")
        self.assertEqual(status, 200)
        self.assertEqual(len(page_one["items"]), 2)
        self.assertIsNotNone(page_one["nextCursor"])
        status, _, page_two = self.call("GET", f"/api/v1/messages/search?boxId={box['id']}&limit=2&cursor={page_one['nextCursor']}")
        self.assertEqual(status, 200)
        self.assertEqual(len(page_two["items"]), 2)
        self.assertTrue({item["id"] for item in page_one["items"]}.isdisjoint({item["id"] for item in page_two["items"]}))
        status, _, problem = self.call("GET", f"/api/v1/messages/search?boxId={box['id']}&limit=101")
        self.assertEqual(status, 400)
        self.assertEqual(problem["code"], "invalid_limit")

    def test_submit_cancel_and_hash_linked_audit(self):
        box = self.create_box("Operations box")
        status, _, message = self.call("POST", "/api/v1/messages", {"boxId": box["id"], "subject": "to submit"}, key="message-submit")
        self.assertEqual(status, 201)
        status, _, operation = self.call("POST", f"/api/v1/messages/{message['id']}/submit", {"targetBoxId": "synthetic-target"}, key="submit")
        self.assertEqual(status, 202)
        status, _, cancelled = self.call("POST", f"/api/v1/operations/{operation['operationId']}/cancel", {}, key="cancel")
        self.assertEqual(status, 202)
        self.assertEqual(cancelled["status"], "cancelled")
        status, _, events = self.call("GET", f"/api/v1/messages/{message['id']}/events")
        self.assertEqual(status, 200)
        self.assertEqual(events["items"][-1]["eventType"], "cancelled")

        status, _, audit = self.call("GET", f"/api/v1/audit/events?boxId={box['id']}&limit=100")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(audit["items"]), 4)
        for previous, current in zip(audit["items"], audit["items"][1:]):
            # API order is newest-first; each older event is linked from the newer event.
            self.assertEqual(previous["previousDigest"], current["eventDigest"])

    def test_problem_json_and_secret_boundary(self):
        status, headers, raw = self.app.handle_request("POST", "/api/v1/boxes", {"Authorization": "Bearer dev:platform"}, {"name": "no-key"})
        problem = json.loads(raw)
        self.assertEqual(status, 400)
        self.assertEqual(headers["content-type"], "application/problem+json")
        self.assertEqual(problem["code"], "idempotency_key_required")
        status, _, problem = self.call("POST", "/api/v1/boxes", {"name": "missing auth"}, token="not-a-token", key="auth-deny")
        self.assertEqual(status, 401)
        self.assertEqual(problem["code"], "invalid_token")

        box = self.create_box("Auth metadata box")
        status, _, problem = self.call("POST", "/api/v1/auth-methods", {"boxId": box["id"], "type": "oidc", "metadata": {"secret": "do-not-store"}}, key="secret-reject")
        self.assertEqual(status, 422)
        self.assertEqual(problem["code"], "secret_not_allowed")

    def test_concurrent_idempotency_claim_has_one_side_effect(self):
        def send(_number):
            headers = {"Authorization": "Bearer dev:platform", "Content-Type": "application/json", "Idempotency-Key": "concurrent-box"}
            status, response_headers, raw = self.app.handle_request("POST", "/api/v1/boxes", headers, {"name": "one durable box"})
            return status, response_headers, json.loads(raw)

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(send, range(100)))
        self.assertEqual({status for status, _, _ in results}, {201})
        self.assertEqual({data["id"] for _, _, data in results}, {results[0][2]["id"]})
        self.assertEqual(self.app.db.one("SELECT COUNT(*) AS count FROM boxes")["count"], 1)
        self.assertEqual(sum(1 for _, headers, _ in results if headers.get("idempotent-replay") == "true"), 99)

    def test_idempotency_claim_recovers_after_route_crash(self):
        original_route = self.app._route
        crashed = True

        def fail_once(*args, **kwargs):
            nonlocal crashed
            if crashed:
                crashed = False
                raise RuntimeError("synthetic crash after durable claim")
            return original_route(*args, **kwargs)

        self.app._route = fail_once
        with self.assertRaises(RuntimeError):
            self.app.handle_request(
                "POST",
                "/api/v1/boxes",
                {"Authorization": "Bearer dev:platform", "Content-Type": "application/json", "Idempotency-Key": "crash-recovery"},
                {"name": "recoverable box"},
            )
        claimed = self.app.db.one("SELECT state, attempts, response_status FROM idempotency_keys WHERE tenant_id='platform' AND actor='platform-admin' AND key='crash-recovery'")
        self.assertEqual((claimed["state"], claimed["attempts"], claimed["response_status"]), ("claimed", 1, 0))

        status, headers, body = self.call("POST", "/api/v1/boxes", {"name": "recoverable box"}, key="crash-recovery")
        self.assertEqual((status, body["name"], headers.get("idempotent-replay")), (201, "recoverable box", None))
        completed = self.app.db.one("SELECT state, attempts, response_status FROM idempotency_keys WHERE tenant_id='platform' AND actor='platform-admin' AND key='crash-recovery'")
        self.assertEqual((completed["state"], completed["attempts"], completed["response_status"]), ("completed", 2, 201))
        self.assertEqual(self.app.db.one("SELECT COUNT(*) AS count FROM boxes WHERE name='recoverable box'")["count"], 1)

    def test_worker_projects_delivery_receipt_and_immutable_evidence(self):
        box = self.create_box("Worker box")
        status, _, message = self.call("POST", "/api/v1/messages", {"boxId": box["id"], "subject": "worker"}, key="worker-message")
        self.assertEqual(status, 201)
        content = base64.b64encode(b"synthetic payload").decode("ascii")
        status, _, attachment = self.call("POST", f"/api/v1/messages/{message['id']}/attachments", {"filename": "payload.txt", "mediaType": "text/plain", "contentBase64": content}, key="worker-attachment")
        self.assertEqual((status, attachment["verified"]), (201, True))
        status, _, operation = self.call("POST", f"/api/v1/messages/{message['id']}/submit", {}, key="worker-submit")
        self.assertEqual((status, operation["status"]), (202, "queued"))
        self.assertEqual(self.app.run_worker(), [{"operationId": operation["operationId"], "status": "delivered", "receiptId": self.app.db.one("SELECT id FROM receipts WHERE operation_id=?", (operation["operationId"],))["id"]}])
        status, _, delivered = self.call("GET", f"/api/v1/operations/{operation['operationId']}")
        self.assertEqual((status, delivered["status"], delivered["attempts"]), (200, "delivered", 1))
        receipt_id = self.app.db.one("SELECT id FROM receipts WHERE operation_id=?", (operation["operationId"],))["id"]
        status, _, receipt = self.call("GET", f"/api/v1/messages/{message['id']}/receipts/{receipt_id}")
        self.assertEqual((status, receipt["status"], receipt["immutable"], receipt["sourceCode"]), (200, "delivered", True, "EV3"))
        self.assertTrue(receipt["rawDigest"].startswith("sha256:"))
        self.assertEqual(receipt["validation"]["status"], "passed")
        self.assertTrue(receipt["rawEvidenceBase64"])
        self.assertEqual(receipt["messageId"], message["id"])
        self.assertEqual(receipt["operationId"], operation["operationId"])
        self.assertTrue(receipt["eventId"] and receipt["auditEventId"])
        self.assertEqual(self.app.db.one("SELECT id FROM message_events WHERE id=? AND message_id=?", (receipt["eventId"], message["id"]))["id"], receipt["eventId"])
        self.assertEqual(self.app.db.one("SELECT id FROM audit_events WHERE id=? AND resource_id=?", (receipt["auditEventId"], receipt_id))["id"], receipt["auditEventId"])

        # The export embeds the exact receipt record, preserving traceability
        # without rewriting the immutable receipt row.
        status, _, export = self.call("POST", "/api/v1/exports", {"boxId": box["id"], "format": "jsonl"}, key="worker-export")
        self.assertEqual(status, 202)
        status, _, fetched_export = self.call("GET", f"/api/v1/exports/{export['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched_export["result"]["receipts"][0]["id"], receipt_id)

    def test_worker_reconciles_post_submit_and_post_receipt_crashes(self):
        box = self.create_box("Crash recovery box")
        status, _, message = self.call("POST", "/api/v1/messages", {"boxId": box["id"], "subject": "crash-recovery"}, key="crash-message")
        self.assertEqual(status, 201)
        status, _, operation = self.call("POST", f"/api/v1/messages/{message['id']}/submit", {}, key="crash-submit")
        self.assertEqual(status, 202)

        with self.assertRaisesRegex(RuntimeError, "after adapter submit"):
            self.app.run_worker(lease_seconds=0, crash_at="post-submit")
        side_effect = self.app.pipeline.side_effect(operation["operationId"])
        self.assertEqual(side_effect["state"], "submitted")
        delivered = self.app.run_worker(lease_seconds=0)
        self.assertEqual(delivered[0]["status"], "delivered")
        self.assertEqual(self.app.db.one("SELECT COUNT(*) AS count FROM receipts WHERE operation_id=?", (operation["operationId"],))["count"], 1)

        status, _, message_two = self.call("POST", "/api/v1/messages", {"boxId": box["id"], "subject": "receipt-crash"}, key="receipt-crash-message")
        self.assertEqual(status, 201)
        status, _, operation_two = self.call("POST", f"/api/v1/messages/{message_two['id']}/submit", {}, key="receipt-crash-submit")
        self.assertEqual(status, 202)
        with self.assertRaisesRegex(RuntimeError, "after receipt persistence"):
            self.app.run_worker(lease_seconds=0, crash_at="post-receipt")
        self.assertEqual(self.app.db.one("SELECT status FROM operations WHERE id=?", (operation_two["operationId"],))["status"], "delivered")
        resumed = self.app.run_worker(lease_seconds=0)
        self.assertEqual(resumed[0]["status"], "delivered")
        self.assertEqual(self.app.db.one("SELECT COUNT(*) AS count FROM receipts WHERE operation_id=?", (operation_two["operationId"],))["count"], 1)

    def test_legal_hold_blocks_tombstone_and_restore_verifies_export(self):
        box = self.create_box("Retention box")
        status, _, export = self.call("POST", "/api/v1/exports", {"boxId": box["id"], "format": "jsonl"}, key="retention-export")
        self.assertEqual(status, 202)
        status, _, hold = self.call("POST", "/api/v1/retention/legal-holds", {"boxId": box["id"], "resourceType": "message", "resourceId": "synthetic-message", "reason": "test evidence"}, key="retention-hold")
        self.assertEqual((status, hold["active"]), (201, True))
        status, _, problem = self.call("POST", "/api/v1/retention/deletion-requests", {"boxId": box["id"], "resourceType": "message", "resourceId": "synthetic-message"}, key="retention-delete-held")
        self.assertEqual((status, problem["code"]), (409, "legal_hold_active"))
        status, _, released = self.call("PATCH", f"/api/v1/retention/legal-holds/{hold['id']}", {"active": False}, key="retention-release")
        self.assertEqual((status, released["active"]), (200, False))
        status, _, tombstone = self.call("POST", "/api/v1/retention/deletion-requests", {"boxId": box["id"], "resourceType": "message", "resourceId": "synthetic-message"}, key="retention-delete")
        self.assertEqual((status, tombstone["status"]), (202, "tombstoned"))
        self.assertEqual((tombstone["dataClass"], tombstone["jobStatus"]), ("ordinary", "completed"))
        status, _, restore = self.call("POST", "/api/v1/retention/restore", {"boxId": box["id"], "exportId": export["id"], "namespace": "restore-test"}, key="retention-restore")
        self.assertEqual((status, restore["verified"], restore["checks"]["blindSendReplay"]), (200, True, False))
        self.assertEqual(restore["policyVersion"], "ag-retention-v1")
        self.assertTrue(restore["checks"]["messageEventHashLinks"])

    def test_restore_fails_closed_when_export_event_manifest_is_tampered(self):
        box = self.create_box("Restore integrity")
        status, _, export = self.call("POST", "/api/v1/exports", {"boxId": box["id"], "format": "jsonl"}, key="restore-integrity-export")
        self.assertEqual(status, 202)
        self.app.db.connection.execute("UPDATE exports SET result_json=? WHERE id=?", (json.dumps({"boxId": box["id"], "policy": {"version": "ag-retention-v1"}, "auditEvents": [{"eventDigest": "sha256:tampered"}]}), export["id"]))
        self.app.db.connection.commit()
        status, _, report = self.call("POST", "/api/v1/retention/restore", {"boxId": box["id"], "exportId": export["id"], "namespace": "restore-integrity"}, key="restore-integrity-run")
        self.assertEqual(status, 200)
        self.assertFalse(report["verified"])
        self.assertFalse(report["checks"]["manifest"])


if __name__ == "__main__":
    unittest.main()
