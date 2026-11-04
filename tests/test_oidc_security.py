import base64
import hashlib
import hmac
import json
import unittest
from datetime import datetime, timezone

from ag_datovka.app import create_app
from ag_datovka.security import TrustError, validate_signed_oidc


def _token(claims, key=b"synthetic-signing-key"):
    def enc(value):
        return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).rstrip(b"=").decode()
    header, body = enc({"alg": "HS256", "typ": "JWT", "kid": "test-1"}), enc(claims)
    signed = f"{header}.{body}".encode()
    signature = base64.urlsafe_b64encode(hmac.new(key, signed, hashlib.sha256).digest()).rstrip(b"=").decode()
    return f"{header}.{body}.{signature}"


class OidcSecurityTest(unittest.TestCase):
    def test_signed_validator_enforces_claims_and_revocation(self):
        claims = {"iss": "https://issuer.synthetic.test", "aud": "ag-datovka-api", "sub": "alice",
                  "tenant": "box-1", "jti": "token-1", "exp": 1_800_000_000}
        token = _token(claims)
        verified = validate_signed_oidc(token, signing_keys={"test-1": b"synthetic-signing-key"},
                                        issuer=claims["iss"], audience=claims["aud"],
                                        now=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual((verified["subject"], verified["tenant"]), ("alice", "box-1"))
        with self.assertRaisesRegex(TrustError, "issuer"):
            validate_signed_oidc(_token({**claims, "iss": "https://attacker.invalid"}), signing_keys={"test-1": b"synthetic-signing-key"}, issuer=claims["iss"], audience=claims["aud"])
        with self.assertRaisesRegex(TrustError, "revoked"):
            validate_signed_oidc(token, signing_keys={"test-1": b"synthetic-signing-key"}, issuer=claims["iss"], audience=claims["aud"], revoked_token_ids=frozenset({"token-1"}))

    def test_unsigned_oidc_shaped_token_and_same_tenant_impersonation_fail(self):
        app = create_app(":memory:", oidc_issuer="https://issuer.synthetic.test", oidc_audience="ag-datovka-api", oidc_signing_keys={"test-1": b"synthetic-signing-key"})
        try:
            def call(method, path, body=None, token="dev:platform", key="k"):
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                if method in {"POST", "PUT", "PATCH", "DELETE"}:
                    headers["Idempotency-Key"] = key
                status, _, raw = app.handle_request(method, path, headers, body or {})
                return status, json.loads(raw)

            status, box = call("POST", "/api/v1/boxes", {"name": "OIDC box"}, key="box")
            self.assertEqual(status, 201)
            status, identity = call("POST", f"/api/v1/boxes/{box['id']}/identities", {"subject": "alice"}, key="identity")
            self.assertEqual(status, 201)
            claims = {"iss": "https://issuer.synthetic.test", "aud": "ag-datovka-api", "sub": f"owner:{box['id']}", "tenant": box["id"], "jti": "token-1", "exp": 1_800_000_000}
            status, result = call("GET", f"/api/v1/boxes/{box['id']}", token=f"oidc:{box['id']}:alice:1800000000:", key="unsigned")
            self.assertEqual((status, result["code"]), (401, "invalid_token"))
            status, result = call("GET", f"/api/v1/boxes/{box['id']}", token=_token(claims), key="signed")
            self.assertEqual((status, result["id"]), (200, box["id"]))
            status, result = call("GET", f"/api/v1/boxes/{box['id']}", token=_token({**claims, "sub": "operator-not-bound"}), key="impersonation")
            self.assertEqual((status, result["code"]), (401, "identity_binding_failed"))
            self.assertEqual(identity["subject"], "alice")
        finally:
            app.close()

    def test_legacy_adapter_is_disabled_for_deploy_profile(self):
        app = create_app(":memory:", auth_profile="deploy")
        try:
            status, _, raw = app.handle_request("GET", "/api/v1", {"Authorization": "Bearer dev:platform"}, {})
            self.assertEqual((status, json.loads(raw)["code"]), (401, "invalid_token"))
        finally:
            app.close()


if __name__ == "__main__":
    unittest.main()
