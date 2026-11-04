import base64
import json
import unittest
from unittest.mock import patch

from ag_datovka import create_app
from ag_datovka.isds_adapter import AdapterError


class SyntheticSendReceiveSliceTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(":memory:")
        self.counter = 0

    def tearDown(self):
        self.app.close()

    def call(self, method, path, body=None, *, key=None):
        self.counter += 1
        headers = {"Authorization": "Bearer dev:platform", "Content-Type": "application/json"}
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            headers["Idempotency-Key"] = key or f"slice-{self.counter}"
        status, _, raw = self.app.handle_request(method, path, headers, body or {})
        return status, json.loads(raw)

    def box(self, name):
        status, result = self.call("POST", "/api/v1/boxes", {"name": name, "kind": "test"})
        self.assertEqual(status, 201)
        return result

    def test_send_receive_evidence_and_retention_recovery(self):
        sender = self.box("Synthetic sender")
        recipient = self.box("Synthetic recipient")
        status, message = self.call("POST", "/api/v1/messages", {"boxId": sender["id"], "subject": "P4-05 synthetic message"}, key="slice-message")
        self.assertEqual(status, 201)
        content = b"synthetic attachment for AGDA-38"
        status, attachment = self.call("POST", f"/api/v1/messages/{message['id']}/attachments", {"filename": "evidence.txt", "mediaType": "text/plain", "contentBase64": base64.b64encode(content).decode()}, key="slice-attachment")
        self.assertEqual((status, attachment["verified"]), (201, True))
        status, operation = self.call("POST", f"/api/v1/messages/{message['id']}/submit", {"targetBoxId": recipient["id"]}, key="slice-submit")
        self.assertEqual((status, operation["status"]), (202, "queued"))

        result = self.app.run_worker()
        receipt_id = self.app.db.one("SELECT id FROM receipts WHERE operation_id=?", (operation["operationId"],))["id"]
        self.assertEqual(result, [{"operationId": operation["operationId"], "status": "delivered", "receiptId": receipt_id}])
        operation_row = self.app.db.one("SELECT * FROM operations WHERE id=?", (operation["operationId"],))
        self.assertEqual(operation_row["status"], "delivered")
        self.assertIsNotNone(operation_row["recipient_message_id"])
        self.assertEqual(self.app.db.one("SELECT status FROM messages WHERE id=?", (operation_row["recipient_message_id"],))["status"], "delivered")
        self.assertEqual(self.app.db.one("SELECT COUNT(*) AS count FROM attachments WHERE message_id=?", (operation_row["recipient_message_id"],))["count"], 1)

        receipt = self.app.db.one("SELECT * FROM receipts WHERE operation_id=?", (operation["operationId"],))
        self.assertEqual((receipt["status"], receipt["source_code"], receipt["immutable"]), ("delivered", "EV3", 1))
        self.assertEqual(self.app.pipeline.side_effect(operation["operationId"])["state"], "reconciled")
        status, inbox = self.call("GET", f"/api/v1/messages/search?boxId={recipient['id']}")
        self.assertEqual((status, len(inbox["items"])), (200, 1))
        self.assertEqual(inbox["items"][0]["status"], "delivered")

        status, export = self.call("POST", "/api/v1/exports", {"boxId": sender["id"], "format": "jsonl"}, key="slice-export")
        self.assertEqual(status, 202)
        status, exported = self.call("GET", f"/api/v1/exports/{export['id']}")
        self.assertEqual((status, len(exported["result"]["receipts"])), (200, 1))
        self.assertEqual(exported["result"]["receipts"][0]["rawDigest"], receipt["raw_digest"])

        status, hold = self.call("POST", "/api/v1/retention/legal-holds", {"boxId": sender["id"], "resourceType": "message", "resourceId": message["id"], "reason": "synthetic evidence"}, key="slice-hold")
        self.assertEqual((status, hold["active"]), (201, True))
        status, problem = self.call("POST", "/api/v1/retention/deletion-requests", {"boxId": sender["id"], "resourceType": "message", "resourceId": message["id"]}, key="slice-delete-held")
        self.assertEqual((status, problem["code"]), (409, "legal_hold_active"))
        status, _ = self.call("PATCH", f"/api/v1/retention/legal-holds/{hold['id']}", {"active": False}, key="slice-release")
        self.assertEqual(status, 200)
        status, tombstone = self.call("POST", "/api/v1/retention/deletion-requests", {"boxId": sender["id"], "resourceType": "message", "resourceId": message["id"]}, key="slice-delete")
        self.assertEqual((status, tombstone["status"]), (202, "tombstoned"))
        status, restore = self.call("POST", "/api/v1/retention/restore", {"boxId": sender["id"], "exportId": export["id"], "namespace": "agda-38-recovery"}, key="slice-restore")
        self.assertEqual((status, restore["verified"], restore["checks"]["blindSendReplay"]), (200, True, False))
        actions = {row["action"] for row in self.app.db.all("SELECT * FROM audit_events WHERE tenant_id=?", (sender["id"],))}
        self.assertTrue({"receipt.validated", "export.created", "retention.deleted"}.issubset(actions))

    def test_delivery_stays_unresolved_when_adapter_receipt_validation_fails(self):
        sender = self.box("Receipt gate sender")
        status, message = self.call("POST", "/api/v1/messages", {"boxId": sender["id"], "subject": "must not deliver"}, key="gate-message")
        self.assertEqual(status, 201)
        status, operation = self.call("POST", f"/api/v1/messages/{message['id']}/submit", {}, key="gate-submit")
        self.assertEqual(status, 202)
        with patch("ag_datovka.app.IsdsCompatibilityAdapter.parse_receipt", side_effect=AdapterError("invalid_receipt", "synthetic invalid receipt")):
            with self.assertRaisesRegex(RuntimeError, "receipt validation failed"):
                self.app.run_worker()
        self.assertEqual(self.app.db.one("SELECT status FROM messages WHERE id=?", (message["id"],))["status"], "submitting")
        self.assertEqual(self.app.db.one("SELECT status FROM operations WHERE id=?", (operation["operationId"],))["status"], "submitting")
        self.assertEqual(self.app.db.one("SELECT COUNT(*) AS count FROM receipts WHERE operation_id=?", (operation["operationId"],))["count"], 0)


if __name__ == "__main__":
    unittest.main()
