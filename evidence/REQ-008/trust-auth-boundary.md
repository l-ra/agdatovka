# REQ-008 trust/auth boundary evidence

Date: 2026-10-30; scope: synthetic local foundation.

Implemented source:

- `ag_datovka/security.py`: fail-closed certificate policy, HTTPS endpoint
  allow-list, secret-store handle validation, and modern caller-auth parser.
- `ag_datovka/app.py`: separate persistence and management routes for trust
  profiles, endpoint profiles, and key handles; legacy `dev:` authentication is
  retained as a compatibility path and does not replace authorization.
- `fixtures/security/trust-vectors.json`: certificate metadata only; no private
  keys, real anchors, accounts, or production hosts.

Negative coverage includes expired, wrong-host, wrong-key-usage, revoked, and
unknown-CA certificates, plus HTTP and embedded-secret rejection. The synthetic
handshake verifier now separately validates the configured chain anchor, SAN and
issuer policy, key usage, revocation, certificate-to-box/application binding,
rotation overlap, and application-auth nonce expiry/replay. Unauthorized SOAP
responses use a stable fault without certificate, token, or endpoint details.
OIDC bearer tokens remain management authentication only; they are never treated
as an ISDS certificate identity.

Verification:

```text
python3 -m unittest tests.test_security_boundary tests.test_oidc_security -v
python3 -m unittest discover -s tests -q
git diff --check
```

The repository contains no private keys, real credentials, or production
endpoints in the synthetic trust fixtures.

The concurrently materialized pipeline tests have unrelated failures in
`tests/test_pipeline.py`; those files are outside this security change.
