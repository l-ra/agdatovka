import base64
import json
import unittest
from pathlib import Path

from ag_datovka.isds_adapter import AdapterError, IsdsCompatibilityAdapter

FIXTURES = Path(__file__).parents[1] / "fixtures" / "isds"


class IsdsAdapterTest(unittest.TestCase):
    def setUp(self):
        self.adapter = IsdsCompatibilityAdapter()

    def load(self, name):
        return json.loads((FIXTURES / name).read_text())

    def test_envelope_attachment_digest_and_large_profile(self):
        event = self.adapter.parse_envelope(self.load("envelope.json"))[0]
        self.assertEqual(event.event_type, "message_envelope_received")
        self.assertEqual(event.data["attachments"][0]["byteLength"], 17)
        large = self.adapter.parse_large_message({"messageId":"synthetic-big-001", "sizeBytes":100*1024*1024, "attachmentCount":50, "endpoint":"ws2"})
        self.assertEqual(large.data["profile"], "VoDZ")

    def test_lifecycle_all_required_codes_are_explicit(self):
        events = [self.adapter.parse_event(item) for item in self.load("lifecycle.json")]
        self.assertEqual([e.source_code for e in events], ["EV0", "EV2", "EV3", "EV5", "EV6", "EV8", "EV11"])
        self.assertEqual(events[3].event_type, "statutory_fiction")

    def test_auth_receipts_and_round_trip_exports(self):
        auth = self.adapter.parse_auth_response(self.load("auth.json")[0])
        self.assertEqual(auth.event_type, "auth_succeeded")
        raw = (FIXTURES / "receipt.xml").read_bytes()
        receipt = self.adapter.parse_receipt(raw)
        self.assertEqual(receipt.data["rawBytes"], len(raw))
        zfo = self.adapter.parse_receipt((FIXTURES / "receipt.zfo").read_bytes(), format="zfo")
        self.assertEqual(zfo.message_id, receipt.message_id)
        self.assertIn(b"synthetic-msg-001", self.adapter.export_evidence(receipt, format="xml"))
        self.assertTrue(self.adapter.export_evidence(receipt, format="zfo").startswith(b"SYNTHETIC-ZFO"))
        self.assertEqual(receipt.data["validation"]["status"], "passed")
        self.assertEqual(base64.b64decode(receipt.data["rawEvidenceBase64"]), raw)

    def test_receipt_signature_chain_and_error_cases_fail_closed(self):
        for attribute, value, code in (("signatureStatus", "invalid", "invalid_receipt_signature"), ("chainStatus", "invalid", "invalid_receipt_chain"), ("errorCode", "INVALID_RECEIPT", "receipt_error")):
            raw = f'<SyntheticReceipt messageId="synthetic-msg-001" status="delivered" {attribute}="{value}" />'.encode()
            with self.assertRaisesRegex(AdapterError, code):
                self.adapter.parse_receipt(raw)

    def test_errors_and_invalid_inputs_are_structured(self):
        error = self.adapter.parse_error(self.load("errors.json")[0])
        self.assertEqual(error.event_type, "upstream_error")
        self.assertTrue(error.data["retryable"])
        with self.assertRaisesRegex(AdapterError, "unsupported ISDS event"):
            self.adapter.parse_event({"messageId":"synthetic-msg", "eventCode":"EV99", "occurredAt":"2026-10-30T00:00:00Z"})
        with self.assertRaisesRegex(AdapterError, "base64"):
            self.adapter.parse_envelope({"messageId":"synthetic-msg", "envelope":{}, "attachments":[{"filename":"x","mediaType":"x","contentBase64":"!"}]})

    def test_fixture_manifest_is_synthetic_and_secret_free(self):
        manifest = self.load("manifest.json")
        self.assertTrue(manifest["syntheticOnly"])
        self.assertIn("production endpoint", manifest["prohibited"])
        self.assertNotIn("password", json.dumps(manifest).lower())


if __name__ == "__main__":
    unittest.main()
