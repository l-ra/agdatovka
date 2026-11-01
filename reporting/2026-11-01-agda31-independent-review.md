# AGDA-31 independent security re-review — 2026-11-01

## Scope and verdict

Reviewed the Phase 3 candidate at commit `140584e0da6fd14170488ab9809f622cc9994544`,
including the management API, trust/authentication boundary, content ingress,
worker/recovery pipeline, UI boundary, retention/restore, observability, fork
workflow, and committed evidence. The review is independent of implementation
ownership and makes no production security certification claim.

**Synthetic verdict:** the former F-001/F-002 authorization and cross-tenant
identity findings are closed, and the F-003/F-004/F-005 closure reproductions
pass in the isolated local fixture. The candidate is **conditionally usable as
synthetic/test-only evidence**.

**Release verdict:** **BLOCKED outside the isolated synthetic fixture** until
F-007 and F-008 below are fixed or explicitly dispositioned by the security
owner. Performance execution, external ISDS delivery, HA/process recovery,
legal compliance, migration, and production interoperability remain unproven
and are not release evidence.

## Reproduced evidence

Commands run from the repository root:

```text
python3 -m py_compile ag_datovka/*.py qa/*.py fork/scripts/*.py
python3 -m unittest discover -s tests -v
python3 -m qa.performance_readiness --validate
fork/scripts/check.sh
python3 fork/scripts/local_workflow.py --manifest /tmp/agda-review-workflow.json
```

Results: compile passed; **58 tests passed**; readiness validation passed
without load execution; fork checks passed; local workflow passed using the
`ag-synthetic` in-process fixture. The workflow manifest explicitly reports
`http://127.0.0.1:0` in-process isolation and no upstream signature/chain.
These are fixture results, not external endpoint proof.

## Finding matrix

| ID | Severity | Status | Owner | Evidence and acceptance criteria |
| --- | --- | --- | --- | --- |
| F-001 | High | Closed in candidate | Backend Management / Security | Tenant policy mutation is now platform-only and the negative regression passes: `tests/test_management_api.py::test_tenant_cannot_mutate_global_policy_or_assign_platform_role`; acceptance: tenant role/permission/trust/endpoint mutation returns `403`, and platform role assignment is denied. |
| F-002 | High | Closed for cross-tenant references | Backend Management / Security | `_identity_in_box` is used for message sender and auth-method bindings; `tests/test_management_api.py::test_cross_tenant_identity_references_are_rejected` returns stable `422 cross_tenant_reference`. Same-tenant acting-as authorization remains F-007. |
| F-003 | Medium | Closed synthetic ingress | Messaging / Backend | `tests/test_qa_conformance.py` verifies received-byte SHA-256, declared length, metadata-only rejection, 16 MiB limit, octet-stream WSGI ingress, and malformed transport lengths. Acceptance is met only for this bounded synthetic API boundary; no external object-store or production streaming proof. |
| F-004 | Medium | Closed synthetic reliability | Messaging / QA | `tests/test_management_api.py::test_concurrent_idempotency_claim_has_one_side_effect`, crash recovery, and `tests/test_pipeline.py` lease/retry/dead-letter/restart tests pass. Acceptance is met for the serialized SQLite fixture, not a multi-process/HA deployment. |
| F-005 | Medium | Deferred, correctly gated | QA / Architecture | Numeric proposals exist in `docs/testing/PERFORMANCE-THRESHOLDS.json`, but `AGDA-30` correctly did not execute load. Acceptance for a performance pass is not met; no p99/error/drain/memory claim may be made. |
| F-006 | Low | Residual reporting hygiene | Release Integration / Public Reporting | Historical foundation report lacks claim-local exact evidence links. The current candidate evidence is substantially more precise, but AGDA-32 should lint public claims against commit and evidence identifiers before publication. |
| F-007 | High | Open; release blocker | Backend Management / Security | `_identity_in_box` checks only active membership in the box, not whether the authenticated actor is authorized to act as that identity. A box owner created identity B, then submitted a message with `senderIdentityId=B`; the route returned `201`. Acceptance: require an explicit actor-to-identity binding or narrowly defined delegated send permission; unauthorized same-tenant sender references return non-leaking `403`/`422`; audit records identify the authorized acting identity. |
| F-008 | High | Open; release blocker outside fixture | Identity / Security | `ag_datovka/security.py::modern_subject` parses an OIDC-shaped bearer string and checks expiry, while `app.py::_authenticate` ignores issuer, audience, signature, and the returned permission claims. A fabricated future-dated token for a known active subject/tenant returned `200` on `GET /api/v1/boxes/{tenant}`. Acceptance: validate a real signed token or make this path an unmistakably test-only adapter that cannot be enabled in a release profile; enforce issuer/audience/tenant/subject binding and revocation semantics. |

## Boundary review summary

- Trust and content fixtures fail closed for the covered malformed, digest,
  certificate, endpoint, secret-handle, and production-host cases.
- Audit and message-event hash chains, receipt digest checks, restore manifest
  checks, legal holds, and blind-send replay prevention passed their synthetic
  tests. Hash chains are tamper evidence in the local store, not a production
  immutability guarantee.
- Redaction tests prevent bearer values, private-key markers, and message
  content from telemetry records. The UI is a static accessible slice, not a
  certification.
- The worker, receipt, fork, restore, and readiness artifacts explicitly state
  synthetic scope. No readiness manifest or offline fixture is treated as
  production proof.

## Sanitized release summary

The Phase 3 candidate passes deterministic synthetic reliability and content
closure tests, including the original tenant-policy and cross-tenant identity
regressions. It is not ready for release beyond the isolated fixture because
same-tenant sender impersonation and unsigned OIDC-shaped authentication still
permit provenance or caller-authentication ambiguity. Performance, external
interoperability, and legal/production claims remain deferred.
