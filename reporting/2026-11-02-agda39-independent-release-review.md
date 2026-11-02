# AGDA-39 / AGDA-33 P4-06R — independent red-team release review

**Review date:** 2026-11-02  
**Candidate reviewed:** `8f85624` (F-007 sender-identity authorization remediation on `d77113e`)
**Reviewer:** Independent Review and Red Team

## Disposition

**No release-blocking finding identified in the covered synthetic boundary.**
The prior F-007 high-severity authorization finding was independently
re-tested after remediation and is closed for this API path. An authenticated
tenant principal claiming another active same-tenant identity now receives a
non-leaking HTTP 403, no message row is created, and the denial is audit
recorded with authenticated and declared identity ids.

The signed-token enforcement finding F-008 is closed in this candidate for the
covered API path. No additional hidden high-severity finding was identified
within the requested review scope (tenant/identity binding, signed tokens,
RBAC, secret handling, production-host exclusion, receipt/delivered claims,
attachment integrity, error redaction, and container boundary). This is not a
production certification: external ISDS, HA/multi-process recovery, provider
trust material, legal compliance, and performance execution remain unproven.

## Verification evidence

Commands run from the repository root:

```text
python3 -m unittest discover -v
```

Result: **69 tests passed**. The suite covers the signed-token, revocation,
tenant-binding, RBAC, secret redaction, production-host fixture scan,
attachment byte/digest/size checks, receipt integrity, delivered projection,
idempotency/recovery, pipeline leases, and non-root runtime assertions.

The focused F-007 regression created a box, created a second active identity,
then authenticated as the owner and submitted:

```json
{
  "boxId": "<owner box>",
  "senderIdentityId": "<second active identity>",
  "subject": "unauthorized acting-as"
}
```

The response is now **HTTP 403** with code `sender_identity_forbidden`; no
message row is persisted. The authorization decision audit event records the
authenticated actor, declared sender, denial, and `actor_identity_binding`
basis. The positive self-send path remains **HTTP 201**. Platform control-plane
send remains an explicit, auditable bypass in the synthetic fixture.

F-008 checks passed independently in `tests/test_oidc_security.py`: unsigned
OIDC-shaped tokens are rejected; compact signed tokens require the configured
HS256 key, issuer, audience, expiry, subject, tenant, and token id; revoked
token ids are rejected; and the signed subject must be an active identity in
the claimed tenant. The deploy profile rejects the legacy `dev:` adapter.

Container/configuration review found the intended non-root UID 10001,
read-only API/worker Compose services, tmpfs-only writable scratch space,
explicit durable deploy endpoints, and secret-manager-only password
injection. No production hostname or credential was found in the reviewed
fixture/configuration evidence. No Docker build or external service startup
was claimed or performed.

## Finding matrix

| ID | Severity | Status | Owner | Acceptance criteria |
| --- | --- | --- | --- | --- |
| F-007 | High / release blocker | Closed for covered synthetic API path | Backend Management / Security | Remediated in `8f85624`; actor identity binding, non-leaking 403, no-row assertion, audit assertion, and positive self-send regression are present in `tests/test_management_api.py`. |
| F-008 | High | Closed for covered synthetic API path | Identity / Security | Signed-token validation and tenant/subject binding are enforced; unsigned legacy tokens are unavailable in deploy/production profiles; revocation is checked. External IdP/JWKS and provider certification remain deployment work. |

## Release handoff

This review deliberately does not self-approve implementation. The covered
synthetic boundary has no remaining high-severity blocker, but this is not a
production certification: external IdP/JWKS, external provider behavior,
HA/multi-process recovery, legal compliance, and performance execution remain
outside this evidence. Review artifact: this file; remediation commit:
`8f85624`; prior candidate: `d77113e`.
