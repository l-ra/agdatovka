import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ag_datovka.security import (TrustError, TrustProfile, validate_certificate, validate_endpoint,
                                 secret_handle, validate_mtls_identity, validate_isds_auth,
                                 unauthorized_soap_fault)


class TrustBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = json.loads(Path("fixtures/security/trust-vectors.json").read_text())
        cls.profile = TrustProfile.from_mapping(data["profile"])
        cls.vectors = data["certificates"]
        cls.now = datetime(2026, 6, 1, tzinfo=timezone.utc)

    def test_valid_certificate_and_all_negative_vectors(self):
        result = validate_certificate(self.vectors["valid"], self.profile, hostname="isds.synthetic.test", now=self.now)
        self.assertEqual(result["status"], "valid")
        for name, code in (("expired", "certificate_expired"), ("wrong-host", "wrong_hostname"), ("wrong-usage", "wrong_key_usage"), ("revoked", "certificate_revoked"), ("unknown-ca", "invalid_chain")):
            with self.subTest(name=name):
                with self.assertRaises(TrustError) as caught:
                    validate_certificate(self.vectors[name], self.profile, hostname="isds.synthetic.test", now=self.now)
                self.assertEqual(caught.exception.code, code)

    def test_endpoint_and_secret_boundaries(self):
        self.assertEqual(validate_endpoint({"scheme": "https", "hostname": "isds.synthetic.test", "allowList": ["isds.synthetic.test"]})["scheme"], "https")
        with self.assertRaises(TrustError):
            validate_endpoint({"scheme": "http", "hostname": "isds.synthetic.test", "allowList": ["isds.synthetic.test"]})
        self.assertEqual(secret_handle({"handle": "vault:synthetic/ag/client", "version": "2"})["version"], "2")
        with self.assertRaises(TrustError):
            secret_handle({"handle": "-----BEGIN PRIVATE KEY-----"})

    def test_mtls_identity_binding_and_rotation_overlap(self):
        result = validate_mtls_identity(self.vectors["valid"], self.profile,
                                        hostname="isds.synthetic.test", box_id="box-1",
                                        bindings={"box-1": {"fingerprint": self.vectors["valid"]["fingerprint"],
                                                            "application": "isds-soap", "state": "overlap"}})
        self.assertEqual((result["boxId"], result["bindingState"]), ("box-1", "overlap"))
        with self.assertRaisesRegex(TrustError, "not bound"):
            validate_mtls_identity(self.vectors["valid"], self.profile, hostname="isds.synthetic.test",
                                   box_id="box-2", bindings={"box-2": "sha256:" + "c" * 64})

    def test_application_auth_expiry_and_replay_are_fail_closed(self):
        nonce = "synthetic_nonce_1234"
        auth = {"boxId": "box-1", "application": "isds-soap", "nonce": nonce,
                "issuedAt": "2026-06-01T00:00:00Z", "expiresAt": "2026-06-01T00:05:00Z"}
        used = set()
        self.assertEqual(validate_isds_auth(auth, box_id="box-1", used_nonces=used,
                                            now=self.now)["status"], "authenticated")
        with self.assertRaisesRegex(TrustError, "already been used"):
            validate_isds_auth(auth, box_id="box-1", used_nonces=used, now=self.now)
        with self.assertRaisesRegex(TrustError, "outside"):
            validate_isds_auth({**auth, "nonce": "synthetic_nonce_5678"}, box_id="box-1",
                               now=datetime(2026, 6, 1, 0, 6, tzinfo=timezone.utc))
        fault = unauthorized_soap_fault("certificate_revoked")
        self.assertIn(b"Authentication failed", fault)
        self.assertNotIn(b"Certificate chain", fault)


if __name__ == "__main__":
    unittest.main()
