import base64
import hashlib
import json
import sqlite3
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from ag_datovka.isds_adapter import AdapterError, IsdsCompatibilityAdapter
from ag_datovka.pipeline import DurablePipeline
from ag_datovka.security import TrustError, TrustProfile, validate_certificate
from ag_datovka.soap_gateway import ISDS_NS, SOAP_ACTIONS, SOAP_ENV, SyntheticSoapGateway


ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "fixtures" / "isds"


class WsdlSchemaConformanceTest(unittest.TestCase):
    def test_pinned_wsdl_and_xsd_have_matching_operation_and_order_contract(self):
        wsdl = ET.parse(FIXTURES / "soap-v20.wsdl").getroot()
        port_type = wsdl.find("{http://schemas.xmlsoap.org/wsdl/}portType")
        operations = [item.attrib["name"] for item in port_type]
        self.assertEqual(operations, list(SOAP_ACTIONS))

        schema = ET.parse(FIXTURES / "soap-v20.xsd").getroot()
        self.assertEqual(schema.attrib["targetNamespace"], ISDS_NS)
        create = schema.find("{http://www.w3.org/2001/XMLSchema}element[@name='CreateMessage']")
        sequence = create.find(".//{http://www.w3.org/2001/XMLSchema}sequence")
        self.assertEqual([item.attrib["name"] for item in sequence], ["messageId", "subject", "recipientBoxId", "attachments"])
        attachment = schema.find(".//{http://www.w3.org/2001/XMLSchema}element[@name='attachment']")
        self.assertEqual((attachment.attrib["minOccurs"], attachment.attrib["maxOccurs"]), ("0", "50"))


class LifecycleAndVoDZConformanceTest(unittest.TestCase):
    def setUp(self):
        self.adapter = IsdsCompatibilityAdapter()

    def test_ev0_to_ev13_matrix_preserves_supported_codes_and_rejects_unmapped_codes(self):
        supported = {"EV0": "submitted", "EV2": "delivered", "EV3": "read", "EV5": "statutory_fiction", "EV6": "undeliverable", "EV8": "delivery_failed", "EV11": "expired"}
        for code, event_type in supported.items():
            with self.subTest(code=code):
                event = self.adapter.parse_event({"messageId": "synthetic-msg", "eventCode": code, "occurredAt": "2026-10-30T00:00:00Z"})
                self.assertEqual((event.source_code, event.event_type), (code, event_type))
        for code in ("EV1", "EV4", "EV7", "EV9", "EV10", "EV12", "EV13"):
            with self.subTest(code=code), self.assertRaises(AdapterError) as caught:
                self.adapter.parse_event({"messageId": "synthetic-msg", "eventCode": code, "occurredAt": "2026-10-30T00:00:00Z"})
            self.assertEqual(caught.exception.code, "unknown_event_code")

    def test_vodz_inclusive_boundaries_and_fail_closed_overages(self):
        for size, count in ((20 * 1024 * 1024, 1), (100 * 1024 * 1024, 50)):
            with self.subTest(size=size, count=count):
                event = self.adapter.parse_large_message({"messageId": "synthetic-big", "sizeBytes": size, "attachmentCount": count, "endpoint": "ws2"})
                self.assertEqual((event.data["profile"], event.data["sizeBytes"], event.data["attachmentCount"]), ("VoDZ", size, count))
        for payload in (
            {"messageId": "synthetic-big", "sizeBytes": 100 * 1024 * 1024 + 1, "attachmentCount": 1, "endpoint": "ws2"},
            {"messageId": "synthetic-big", "sizeBytes": 100 * 1024 * 1024, "attachmentCount": 51, "endpoint": "ws2"},
            {"messageId": "synthetic-big", "sizeBytes": 20 * 1024 * 1024, "attachmentCount": 1, "endpoint": "ws"},
        ):
            with self.subTest(payload=payload), self.assertRaises(AdapterError) as caught:
                self.adapter.parse_large_message(payload)
            self.assertIn(caught.exception.code, {"large_message_limit", "invalid_large_message_endpoint"})

    def test_receipt_raw_bytes_are_digestable_and_round_trip_exactly(self):
        raw = (FIXTURES / "receipt.xml").read_bytes()
        receipt = self.adapter.parse_receipt(raw)
        self.assertEqual(receipt.data["rawDigest"], "sha256:" + hashlib.sha256(raw).hexdigest())
        self.assertEqual(base64.b64decode(receipt.data["rawEvidenceBase64"]), raw)
        self.assertEqual(self.adapter.export_evidence(receipt, format="json").count(b"synthetic-msg-001"), 1)


class SoapFaultAndTrustConformanceTest(unittest.TestCase):
    def setUp(self):
        self.gateway = SyntheticSoapGateway()
        self.raw = (FIXTURES / "soap-create-message.xml").read_bytes()
        self.headers = {"soapaction": SOAP_ACTIONS["CreateMessage"], "x-request-id": "req_agda62", "correlation-id": "corr_agda62"}

    def test_fault_matrix_preserves_safe_correlation_and_raw_provenance(self):
        cases = [
            ("GET", "/isds/ws", self.raw, "Client.MethodNotAllowed"),
            ("POST", "/isds/nope", self.raw, "Client.Endpoint"),
            ("POST", "/isds/ws", b"<broken", "Client.MalformedXML"),
            ("POST", "/isds/ws", self.raw, "Client.MissingSOAPAction"),
        ]
        for method, path, raw, code in cases:
            headers = {"x-request-id": "req_missing"} if code == "Client.MissingSOAPAction" else self.headers
            with self.subTest(code=code):
                status, _, response, exchange = self.gateway.handle(method, path, headers, raw)
                self.assertIn(code.encode(), response)
                self.assertEqual(exchange.raw_xml, raw)
                self.assertIsNotNone(exchange.upstream_fault)
                self.assertIsNone(exchange.normalized_result)
                self.assertIn((b"req_missing" if code == "Client.MissingSOAPAction" else b"corr_agda62"), response)
                self.assertEqual(status, 405 if code == "Client.MethodNotAllowed" else 404 if code == "Client.Endpoint" else 400)

    def test_trust_negative_matrix_is_explicit(self):
        data = json.loads((ROOT / "fixtures/security/trust-vectors.json").read_text())
        profile = TrustProfile.from_mapping(data["profile"])
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        expected = {"expired": "certificate_expired", "wrong-host": "wrong_hostname", "wrong-usage": "wrong_key_usage", "revoked": "certificate_revoked", "unknown-ca": "invalid_chain"}
        for name, code in expected.items():
            with self.subTest(name=name), self.assertRaises(TrustError) as caught:
                validate_certificate(data["certificates"][name], profile, hostname="isds.synthetic.test", now=now)
            self.assertEqual(caught.exception.code, code)


class RetryAndIdempotencyEvidenceTest(unittest.TestCase):
    def test_retry_key_and_receipt_evidence_survive_reinstantiation(self):
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        pipeline = DurablePipeline(connection, max_attempts=3, base_backoff_seconds=1)
        now = datetime(2026, 10, 30, tzinfo=timezone.utc)
        self.assertTrue(pipeline.enqueue("op-agda62", "msg-agda62", '{"messageId":"msg-agda62"}', now=now))
        pipeline.dispatch(now=now)
        item = pipeline.claim("synthetic-worker", now=now)
        prepared = pipeline.prepare_side_effect(item, now=now)
        self.assertEqual(prepared["idempotencyKey"], "op-agda62:attempt:1")
        pipeline.record_side_effect(item, state="submitted", evidence={"rawDigest": "sha256:" + "0" * 64}, adapter_status="accepted", now=now)
        restarted = DurablePipeline(connection, max_attempts=3, base_backoff_seconds=1)
        evidence = restarted.side_effect("op-agda62")
        self.assertEqual((evidence["state"], evidence["adapterStatus"], evidence["evidence"]["rawDigest"]), ("submitted", "accepted", "sha256:" + "0" * 64))


if __name__ == "__main__":
    unittest.main()
