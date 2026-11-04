import json
import unittest
from pathlib import Path

from ag_datovka.app import create_app
from ag_datovka.soap_gateway import ISDS_NS, SOAP_ACTIONS, SOAP_ENV, SyntheticSoapGateway

FIXTURES = Path(__file__).parents[1] / "fixtures" / "isds"


class SoapGatewayTest(unittest.TestCase):
    def setUp(self):
        self.gateway = SyntheticSoapGateway()
        self.raw = (FIXTURES / "soap-create-message.xml").read_bytes()
        self.headers = {"content-type": "text/xml; charset=utf-8", "soapaction": SOAP_ACTIONS["CreateMessage"], "x-request-id": "req_synthetic_001", "correlation-id": "corr_synthetic_001"}

    def test_positive_soap11_preserves_correlation_and_normalizes_attachment(self):
        status, headers, response, exchange = self.gateway.handle("POST", "/isds/ws", self.headers, self.raw)
        self.assertEqual(status, 200)
        self.assertEqual(headers["x-request-id"], "req_synthetic_001")
        self.assertIsNone(exchange.upstream_fault)
        self.assertEqual(exchange.normalized_result["event"]["data"]["attachments"][0]["byteLength"], 17)
        self.assertIn(b"CreateMessageResponse", response)
        self.assertIn(b"corr_synthetic_001", response)

    def test_wsgi_integration_isolated_from_management_auth(self):
        app = create_app()
        status, headers, response = app.handle_request("POST", "/isds/ws", self.headers, self.raw)
        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "text/xml; charset=utf-8")
        app.close()

    def test_negative_namespace_sequence_attachment_and_action_faults(self):
        cases = [
            (self.raw.replace(b"http://schemas.xmlsoap.org/soap/envelope/", b"urn:not-soap"), "Client.Namespace"),
            ((FIXTURES / "soap-negative.xml").read_bytes(), "Client.Sequence"),
            (self.raw.replace(b"c3ludGhldGljIGNvbnRlbnQ=", b"!"), "Client.InvalidMessage"),
        ]
        for payload, code in cases:
            status, _, response, exchange = self.gateway.handle("POST", "/isds/ws", self.headers, payload)
            self.assertEqual(status, 400)
            self.assertIn(code.encode(), response)
            self.assertIsNotNone(exchange.upstream_fault)
            self.assertIsNone(exchange.normalized_result)
        status, _, response, _ = self.gateway.handle("POST", "/isds/ws", {**self.headers, "soapaction": "urn:isds:Wrong"}, self.raw)
        self.assertEqual(status, 400)
        self.assertIn(b"Client.SOAPAction", response)

    def test_unsupported_operation_and_endpoint(self):
        payload = self.raw.replace(b"CreateMessage", b"SecretOperation")
        status, _, response, _ = self.gateway.handle("POST", "/isds/ws", {**self.headers, "soapaction": "urn:isds:SecretOperation"}, payload)
        self.assertEqual(status, 400)
        self.assertIn(b"Client.UnsupportedOperation", response)
        status, _, response, _ = self.gateway.handle("POST", "/isds/ws2", self.headers, self.raw)
        self.assertEqual(status, 400)
        self.assertIn(b"Client.Endpoint", response)

    def test_missing_required_element_is_a_sequence_fault(self):
        payload = self.raw.replace(b"<isds:subject>Synthetic notice</isds:subject>", b"")
        status, _, response, exchange = self.gateway.handle("POST", "/isds/ws", self.headers, payload)
        self.assertEqual(status, 400)
        self.assertIn(b"Client.Sequence", response)
        self.assertIsNotNone(exchange.upstream_fault)

    def test_fixture_manifest_has_pinned_hashes_and_is_synthetic(self):
        manifest = json.loads((FIXTURES / "soap-manifest.json").read_text())
        self.assertTrue(manifest["syntheticOnly"])
        self.assertRegex(manifest["evidence"]["soap-v20.wsdl"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(manifest["evidence"]["soap-v20.xsd"]["sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
