import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ag_datovka.security import TrustError, TrustProfile, validate_certificate, validate_endpoint, secret_handle


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


if __name__ == "__main__":
    unittest.main()
