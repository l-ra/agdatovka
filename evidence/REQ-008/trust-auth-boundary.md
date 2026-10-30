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
unknown-CA certificates, plus HTTP and embedded-secret rejection. Rotation is
represented by versioned handles and staged state; the provider handshake must
complete before an active handle is switched.

Verification: `python3 -m unittest tests.test_security_boundary
tests.test_management_api -q`.

The concurrently materialized pipeline tests have unrelated failures in
`tests/test_pipeline.py`; those files are outside this security change.
