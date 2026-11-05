import json
import unittest
from datetime import timedelta
from pathlib import Path

from ag_datovka.app import create_app
from ag_datovka.isds_adapter import IsdsCompatibilityAdapter
from ag_datovka.security import SYNTHETIC_REFERENCE_NOW, synthetic_application_auth, synthetic_client_certificate
from ag_datovka.soap_gateway import ISDS_NS, SOAP_ACTIONS, SOAP_ENV, SyntheticSoapGateway

FIXTURES = Path(__file__).parents[1] / "fixtures" / "isds"


def synthetic_auth(nonce="synthetic_nonce_soap_001"):
    certificate = synthetic_client_certificate(SYNTHETIC_REFERENCE_NOW)
    application_auth = synthetic_application_auth(box_id="synthetic-box-002", nonce=nonce, now=SYNTHETIC_REFERENCE_NOW)
    return {
        "x-isds-client-certificate": json.dumps(certificate),
        "x-isds-application-auth": json.dumps(application_auth),
    }


class SoapGatewayTest(unittest.TestCase):
    def setUp(self):
        self.gateway = SyntheticSoapGateway(now=SYNTHETIC_REFERENCE_NOW)
        self.raw = (FIXTURES / "soap-create-message.xml").read_bytes()
        self.headers = {"content-type": "text/xml; charset=utf-8", "soapaction": SOAP_ACTIONS["CreateMessage"], "x-request-id": "req_synthetic_001", "correlation-id": "corr_synthetic_001", **synthetic_auth()}

    def test_positive_soap11_preserves_correlation_and_normalizes_attachment(self):
        status, headers, response, exchange = self.gateway.handle("POST", "/isds/ws", self.headers, self.raw)
        self.assertEqual(status, 200)
        self.assertEqual(headers["x-request-id"], "req_synthetic_001")
        self.assertIsNone(exchange.upstream_fault)
        self.assertEqual(exchange.normalized_result["event"]["data"]["attachments"][0]["byteLength"], 17)
        self.assertIn(b"CreateMessageResponse", response)
        self.assertIn(b"corr_synthetic_001", response)

    def test_wsgi_integration_isolated_from_management_auth(self):
        app = create_app(soap_now=SYNTHETIC_REFERENCE_NOW)
        status, headers, response = app.handle_request("POST", "/isds/ws", self.headers, self.raw)
        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "text/xml; charset=utf-8")
        app.close()

    def test_missing_or_wrong_soap_identity_fails_before_adapter_side_effect(self):
        class SideEffectAdapter:
            def __init__(self):
                self.called = False

            def parse_envelope(self, payload):
                self.called = True
                raise AssertionError("adapter must not run before SOAP authentication")

        adapter = SideEffectAdapter()
        gateway = SyntheticSoapGateway(adapter, now=SYNTHETIC_REFERENCE_NOW)
        for label, headers in (
            ("missing", {key: value for key, value in self.headers.items() if not key.startswith("x-isds-")}),
            ("wrong certificate", {**self.headers, "x-isds-client-certificate": self.headers["x-isds-client-certificate"].replace("b" * 64, "c" * 64)}),
            ("wrong box binding", {**self.headers, "x-isds-application-auth": self.headers["x-isds-application-auth"].replace("synthetic-box-002", "synthetic-box-999")}),
            ("wrong application", {**self.headers, "x-isds-application-auth": self.headers["x-isds-application-auth"].replace("isds-soap", "other-app")}),
        ):
            with self.subTest(label=label):
                status, _, response, exchange = gateway.handle("POST", "/isds/ws", headers, self.raw)
                self.assertEqual(status, 401)
                self.assertIn(b"Client.Authentication", response)
                self.assertIsNone(exchange.normalized_result)
                self.assertFalse(adapter.called)

    def test_expired_and_replayed_nonce_fail_before_adapter_side_effect(self):
        gateway = SyntheticSoapGateway(now=SYNTHETIC_REFERENCE_NOW)
        expired = {
            **self.headers,
            "x-isds-application-auth": json.dumps(
                synthetic_application_auth(
                    box_id="synthetic-box-002",
                    nonce="synthetic_nonce_expired",
                    now=SYNTHETIC_REFERENCE_NOW - timedelta(days=1),
                )
            ),
        }
        status, _, response, _ = gateway.handle("POST", "/isds/ws", expired, self.raw)
        self.assertEqual(status, 401)
        self.assertIn(b"Client.Authentication", response)
        self.assertEqual(gateway.handle("POST", "/isds/ws", self.headers, self.raw)[0], 200)
        status, _, response, exchange = gateway.handle("POST", "/isds/ws", self.headers, self.raw)
        self.assertEqual(status, 401)
        self.assertIn(b"Client.Authentication", response)
        self.assertIsNone(exchange.normalized_result)

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

    def test_exactly_50_attachments_pass_and_51_fails_before_normalization(self):
        item = (
            b"<isds:attachment><isds:filename>synthetic.txt</isds:filename>"
            b"<isds:mediaType>text/plain</isds:mediaType>"
            b"<isds:contentBase64>c3ludGhldGlj</isds:contentBase64></isds:attachment>"
        )
        opening = self.raw.split(b"<isds:attachments>", 1)[0] + b"<isds:attachments>"
        closing = b"</isds:attachments></isds:CreateMessage></soapenv:Body></soapenv:Envelope>"

        class CountingAdapter(IsdsCompatibilityAdapter):
            def __init__(self):
                super().__init__()
                self.calls = 0

            def parse_envelope(self, payload):
                self.calls += 1
                return super().parse_envelope(payload)

        adapter = CountingAdapter()
        gateway = SyntheticSoapGateway(adapter, now=SYNTHETIC_REFERENCE_NOW)
        pass_payload = opening + item * 50 + closing
        status, _, _, exchange = gateway.handle("POST", "/isds/ws", self.headers, pass_payload)
        self.assertEqual(status, 200)
        self.assertIsNotNone(exchange.normalized_result)
        self.assertEqual(adapter.calls, 1)

        fail_payload = opening + item * 51 + closing
        first = gateway.handle("POST", "/isds/ws", self.headers, fail_payload)
        second = gateway.handle("POST", "/isds/ws", self.headers, fail_payload)
        self.assertEqual(first[0], 400)
        self.assertIn(b"Client.AttachmentLimit", first[2])
        self.assertEqual(first[2], second[2])
        self.assertIsNone(first[3].normalized_result)
        self.assertIsNotNone(first[3].upstream_fault)
        self.assertEqual(adapter.calls, 1)

    def test_fixture_manifest_has_pinned_hashes_and_is_synthetic(self):
        manifest = json.loads((FIXTURES / "soap-manifest.json").read_text())
        self.assertTrue(manifest["syntheticOnly"])
        self.assertRegex(manifest["evidence"]["soap-v20.wsdl"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(manifest["evidence"]["soap-v20.xsd"]["sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
