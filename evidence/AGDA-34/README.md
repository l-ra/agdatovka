# AGDA-34 security evidence

The Phase 4 security blockers are dispositioned in the integrated candidate:

* F-007 is closed: signed-token `sub` is resolved to an active identity in the
  signed `tenant`; an unbound subject is rejected before authorization.
* F-008 is closed: unsigned `oidc:`-shaped values are rejected and signed
  tokens require HS256 verification, configured issuer and audience, `exp`,
  `jti` revocation, tenant, and subject claims.
* The legacy `dev:` adapter is retained only for synthetic compatibility and
  is disabled for `deploy` and `production` auth profiles.

Evidence: `tests/test_oidc_security.py` covers valid signed authentication,
issuer and revocation failures, unsigned-token rejection, same-tenant
impersonation/binding failure, and deploy-profile legacy-adapter rejection.
Run with `python -m unittest tests.test_oidc_security tests.test_management_api`.

This evidence uses synthetic keys and identifiers only. It does not exercise a
production identity provider, endpoint, deployment, or credential.
