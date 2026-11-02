# AGDA-39 / AGDA-33 P4-06R — independent red-team release review

**Review date:** 2026-11-02  
**Candidate reviewed:** `d77113e` (`AGDA-38` synthetic send/receive vertical slice)  
**Reviewer:** Independent Review and Red Team

## Disposition

**BLOCKED for release beyond the isolated synthetic fixture.** F-007 remains a
high-severity authorization finding: an authenticated tenant principal can
claim another active identity in the same tenant as the message sender. This
can forge message provenance and sender attribution.

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

Result: **68 tests passed**. The suite covers the signed-token, revocation,
tenant-binding, RBAC, secret redaction, production-host fixture scan,
attachment byte/digest/size checks, receipt integrity, delivered projection,
idempotency/recovery, pipeline leases, and non-root runtime assertions.

The focused F-007 reproduction created a box, created a second active identity,
then authenticated as the owner and submitted:

```json
{
  "boxId": "<owner box>",
  "senderIdentityId": "<second active identity>",
  "subject": "unauthorized acting-as"
}
```

The response was **HTTP 201** and persisted the second identity as
`senderIdentityId`. The relevant implementation is
`ag_datovka/app.py::_messages` calling `_identity_in_box`, which verifies only
same-box active membership. It does not verify that the authenticated actor is
the selected identity or has an explicit delegated-send permission.

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
| F-007 | High / release blocker | Reopened; not closed | Backend Management / Security | Require the authenticated actor to equal the selected sender identity, or require a narrowly scoped, auditable delegated-send grant. Unauthorized same-tenant sender references must return non-leaking `403`/`422`; the audit record must identify the authenticated and acting identities. Add a negative regression covering owner/operator claiming another active identity. |
| F-008 | High | Closed for covered synthetic API path | Identity / Security | Signed-token validation and tenant/subject binding are enforced; unsigned legacy tokens are unavailable in deploy/production profiles; revocation is checked. External IdP/JWKS and provider certification remain deployment work. |

## Release handoff

This review deliberately does not self-approve implementation. Release
integration must remain blocked until F-007 has an independently reviewable
fix and regression evidence. Review artifact: this file; candidate commit:
`d77113e`.

