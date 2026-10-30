# AGDA-14 independent security re-review — 2026-10-30

## Verdict

**PASS for the two AGDA-12 High-finding remediations; FAIL for release beyond
the synthetic/local fixture.** The remediation commit reviewed was
`72d8d58f801a9820873982d9cc382796aa193009`. No production endpoint,
credential, account, or real message data was used.

The prior High findings are closed in the reviewed code: tenant callers are
blocked from global policy resources, and cross-box or inactive identity
references are rejected. The repository is not release-ready as a production,
compatibility, or performance implementation because the residual findings
below remain open.

## Verification performed

- `python3 -m unittest discover -s tests -v`: **29 tests passed**.
- Focused tests passed: `test_tenant_cannot_mutate_global_policy_or_assign_platform_role`,
  `test_cross_tenant_identity_references_are_rejected`, trust negative vectors,
  queue recovery/idempotency, export/audit linkage, and fixture secret/host scans.
- Synthetic malformed-input probe reproduced an uncaught `ValueError` for
  attachment `byteLength="not-an-int"`.
- Repository fixture scan found no checked-in production credential or private
  key; production-host rejection tests passed. Textual production-host matches
  are documentation and negative-test fixtures, not runtime endpoints.

## Prior High findings — remediated

### F-001 (prior High): tenant owner could mutate global policy — CLOSED

- **Evidence:** `ag_datovka/app.py:612-646` uses `_require_platform` for role
  and permission list/create; `:440-479` does the same for trust and endpoint
  profiles; `:556-559` prevents tenant assignment of `platform-admin`.
- **Regression:** `tests/test_management_api.py:62-76` proves tenant denial.
- **Acceptance:** Box-owner requests to create/enumerate global policy return
  `403`; platform control-plane requests remain the only allowed path. No
  residual tenant role/permission records are introduced by the tested routes.

### F-002 (prior High): cross-tenant identity references — CLOSED

- **Evidence:** `ag_datovka/app.py:648-667` and `:683-689` call
  `_identity_in_box`; `:858-863` requires an active identity with the target
  box ID. The database rows persist the validated reference only.
- **Regression:** `tests/test_management_api.py:78-87` proves cross-box sender
  and auth-method references return `422/cross_tenant_reference`.
- **Acceptance:** Same-box active references are accepted under permission;
  cross-box and inactive references fail closed without revealing the identity.

## Residual findings

### F-003 — Concurrent idempotency race (Medium; release blocker)

- **Evidence:** `ag_datovka/app.py:330-340` performs replay lookup before the
  route, while `:346-351` inserts the key only after the side effect. There is
  no atomic claim/in-progress state. Two concurrent first requests can both
  route; one then receives an uncaught SQLite uniqueness error, and the
  external/message side effect may already have occurred twice.
- **Impact:** Violates the stated one-logical-operation guarantee under timeout
  or concurrent retry. The sequential test does not exercise this race.
- **Owner:** Backend / Messaging.
- **Acceptance:** Atomically claim `(tenant, actor, key)` before routing; same
  body under 100 concurrent requests yields one durable operation and replay;
  different body yields `409`; no uncaught database error; crash/restart
  recovery records attempt and response state.

### F-004 — Attachment metadata can cause an uncaught 500 (Medium; release blocker)

- **Evidence:** `ag_datovka/app.py:717-722` executes `int(body["byteLength"])`
  without catching `TypeError`/`ValueError`. The synthetic probe with
  `byteLength="not-an-int"` raised `ValueError` out of `handle_request`.
- **Impact:** Malformed large-message input can bypass the structured Problem
  response contract and consume an application worker; this is an input abuse
  and availability gap.
- **Owner:** Messaging / API.
- **Acceptance:** Non-integer, non-finite, missing, negative, and oversized
  lengths return deterministic `400`/`413` Problem JSON, create no attachment,
  and are covered by direct WSGI and contract tests.

### F-005 — HTTP attachment path accepts unverifiable caller-supplied digest
 (Medium; release blocker for content/compatibility claims)

- **Evidence:** `ag_datovka/app.py:710-728` rejects non-JSON bytes but stores
  the JSON `byteLength` and `contentDigest` without receiving or hashing the
  content. `docs/management/openapi.v1.json:60-62` describes a production
  streaming boundary while exposing the metadata-only local fixture body.
  `tests/test_qa_conformance.py:64-70` verifies only the asserted metadata.
- **Impact:** A caller can claim arbitrary content length/digest; audit/export
  evidence is not bound to bytes. This cannot support the documented checksum,
  resumability, malware/parser, or large-message compatibility claims.
- **Owner:** Messaging / Storage.
- **Acceptance:** Either explicitly remove/fixture-label the production claim
  everywhere, or implement bounded streaming into the content store with
  server-computed digest, mismatch rejection, resume/duplicate protection,
  type/size limits, and end-to-end WSGI tests.

### F-006 — Performance and compatibility evidence remains unexecuted (Low;
 release blocker outside synthetic scope)

- **Evidence:** `docs/testing/PERFORMANCE-SCENARIOS.md:3-6,23-32` marks all
  scenarios “Defined, not run”; `docs/testing/PERFORMANCE-THRESHOLDS.json`
  leaves p99, error, drain, and memory limits as `pre_run_agreed`. The
  foundation report correctly says no production interoperability or server
  deployment is proven (`reporting/2026-10-30-foundation.md:17-31`).
- **Impact:** There is no independently reproducible basis for throughput,
  latency, recovery, or external compatibility claims.
- **Owner:** QA / Release Integration.
- **Acceptance:** Keep the release explicitly synthetic-only until the
  approved synthetic runs produce commit/profile/seed/count/latency/queue/
  checksum evidence and numeric thresholds, and compatibility runs exercise
  the actual supported boundary.

## Trust, audit, and isolation conclusion

Trust-profile parsing, endpoint allow-listing, secret-handle validation, OIDC
expiry/tenant parsing, message/search/export/operation box scoping, audit hash
linking, queue leases, retry/dead-letter behavior, and fixture secret/host
guards were reviewed and covered by passing tests. These controls reduce risk
in the synthetic fixture but do not compensate for the open replay/content
findings or authorize production use. Audit and export evidence remain local
SQLite fixture behavior and have not been demonstrated against tamper,
concurrent crash, or restore scenarios.

## Release recommendation

**Do not release outside the isolated synthetic/test environment.** Accept the
AGDA-12 High remediations as verified, retain AGDA-14 open findings F-003–F-006
with the owners and acceptance criteria above, and require a later independent
review after remediation. This adverse verdict is complete review work; it is
not a request for parent-task writes or a production deployment.
