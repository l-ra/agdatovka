# AGDA-68 SOAP trust/auth boundary evidence

Date: 2026-11-04; scope: synthetic offline SOAP route.

Before this change, `ManagementApp._handle_request_unlocked` dispatched
`/isds/ws` directly to `SyntheticSoapGateway`, and a syntactically valid SOAP
request reached normalization without an ISDS identity. Management bearer
identity was not required and is not a valid substitute for the ISDS identity.

The deployed synthetic entry point now verifies, before adapter normalization:

- synthetic client certificate chain facts, hostname/SAN, issuer, validity,
  revocation, key usage, and certificate-to-box/application binding;
- separate application authentication bound to the same box and
  `isds-soap` application, with issued/expiry timestamps and one-time nonce;
- stable authentication faults with no trust or credential details.

The verifier uses only generated synthetic metadata. No live endpoint,
production credential, private key, real certificate, or private user data is
present.

## Automated evidence

```text
python3 -m unittest tests.test_soap_gateway tests.test_agda62_conformance -q
```

The focused suite passes. `tests.test_soap_gateway` includes a positive
authenticated request and negative cases for missing auth, wrong certificate,
wrong box binding, expired nonce, replayed nonce, and wrong application. The
negative test uses an adapter spy and asserts it is not called.

## Limitation boundary

This is an offline synthetic verifier and not a production PKI, TLS
termination, OIDC provider, or live ISDS integration. Certificate metadata is
fixture policy input; production deployment must provide an atomic durable
nonce store and real transport/PKI integration through separately reviewed
components.
