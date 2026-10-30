# Independent foundation review — 2026-10-30

## Scope and disposition

Reviewed commit `111597ade20188581515939177251a8f2c3ff4af` and the current
foundation documents, management API fixture, tests, release runbook, source
register, compatibility plans, and public report. The review is **FAIL for
release outside an isolated synthetic fixture**. The documents correctly mark
many future controls as specified or deferred, but the local foundation has
authorization and integrity defects that must be fixed before it is used as
security evidence or as a compatibility baseline.

Evidence commands:

```text
python3 -m unittest -v                         # Ran 0 tests; discovery gap
python3 -m unittest discover -s tests -v       # required explicit discovery
```

The focused synthetic reproduction created two boxes, used the first box
owner token, and demonstrated that the owner could create a global role and
that a message in box 1 accepted an identity from box 2 as its sender.

## Findings

### F-001 — Tenant owner can mutate global policy (High)

- **Evidence:** `ag_datovka/app.py:530-564,752-764`; the built-in
  `box-owner` role receives every permission except `box:create` at lines
  223-225. `/roles` and `/permissions` call `_require(..., None)`, which
  resolves `None` to the actor's box in the membership query. A box owner can
  therefore create global roles/permissions, and the new role is assignable in
  other boxes. Reproduced with a box-owner token: `POST /api/v1/roles` returned
  `201`.
- **Impact:** A tenant-scoped principal can alter policy objects shared by all
  tenants and prepare privileges for cross-tenant access. This contradicts the
  API trust model's separate platform administration boundary.
- **Owner:** Backend Management / Security.
- **Remediation:** Make role/permission administration explicitly platform
  scoped, or introduce tenant-owned policy records with a `tenant_id` and
  enforce it in every role lookup and membership assignment. Remove
  `policy:manage` from `box-owner` unless the permission is strictly tenant
  scoped. Add cross-tenant negative tests for create/list/assign.
- **Acceptance criteria:** A box-owner request to create or alter a global
  role/permission returns `403`; platform administration remains auditable;
  role lookup cannot select a policy record from another tenant; tests prove a
  role created for tenant A cannot be assigned in tenant B.

### F-002 — Cross-tenant identity references are accepted (High)

- **Evidence:** `ag_datovka/app.py:593-603` stores caller-supplied
  `senderIdentityId` without checking that it belongs to the message's box or
  that the caller may act as that identity. `:566-583` similarly stores an
  arbitrary `identityId` on an auth method without checking its box. The
  focused reproduction created an identity in box 2 and successfully created a
  box-1 message carrying that identity (`201`).
- **Impact:** Audit and message provenance can be forged across tenants;
  later delivery/authentication code could use the wrong credential binding.
  This violates the stated tenant-isolation and certificate/key separation
  boundaries even before an upstream adapter exists.
- **Owner:** Backend Management / Security.
- **Remediation:** Resolve every referenced identity under the target box in
  the same transaction; require active status and an authorization binding for
  the acting subject. Apply the same check to auth-method identity bindings,
  sender identity, attachment/message references, and target-box policy.
- **Acceptance criteria:** Cross-box or disabled identity references return a
  non-leaking `404`/`422`; same-box active references succeed only with the
  required permission; audit records contain the validated identity and box;
  negative tests cover both message creation and auth-method registration.

### F-003 — Streaming/content boundary is not implemented by the server (Medium)

- **Evidence:** `docs/management/API-CONTRACT.md` and
  `docs/compatibility/PUBLIC-INTERFACES.md` describe streamed/resumable
  content, but `docs/management/openapi.v1.json` defines the attachment body as
  generic JSON and `ag_datovka/app.py:622-640` accepts only metadata/digest.
  `ag_datovka/server.py:18-22` runs this fixture directly with the WSGI app;
  non-JSON uploads are rejected as `415` rather than streamed to storage.
- **Impact:** The repository cannot substantiate bounded-memory, checksum,
  resume, malware/parser, or large-message compatibility claims. A caller can
  also assert an arbitrary `byteLength` and digest because no bytes are
  verified in this boundary.
- **Owner:** Messaging / Backend.
- **Remediation:** Either label the local API as metadata-only fixture-only in
  all machine-readable contracts, or implement bounded streaming upload,
  digest verification, resumable state, object-store reference checks, and
  content/type limits before calling it an API foundation.
- **Acceptance criteria:** A synthetic upload's stored digest is computed from
  received bytes; mismatch and over-limit requests fail deterministically;
  interrupted resume does not duplicate bytes; memory remains bounded; the
  contract test exercises the real server path.

### F-004 — Idempotency/concurrency evidence is absent from the implementation (Medium)

- **Evidence:** `docs/architecture/BOUNDARIES.md` and
  `docs/testing/PERFORMANCE-SCENARIOS.md` require replay-safe workers and
  concurrent idempotency tests, but the fixture has no worker/queue or lease
  implementation. In `ag_datovka/app.py:309-329`, replay lookup and insert are
  separate operations with no transaction/claim protecting concurrent first
  requests; the unique primary key can turn a concurrent duplicate into an
  unhandled database error. The existing test only performs sequential replay.
- **Impact:** A timeout/retry race can create an untracked second operation or
  a 500, and the stated one-logical-operation guarantee is not evidenced.
- **Owner:** Messaging / QA.
- **Remediation:** Atomically claim `(tenant, actor, key)` before routing, bind
  it to canonical method/path/body, and make response persistence/recovery
  explicit. Add crash-point and concurrent replay tests, including external
  side-effect reconciliation.
- **Acceptance criteria:** 100 concurrent same-body requests yield one durable
  operation and replay responses; different bodies yield `409`; no request
  returns an uncaught database error; restart/recovery evidence records the
  operation and attempt state.

### F-005 — Deferred performance scenarios lack measurable p99/error limits (Medium)

- **Evidence:** `docs/testing/PERFORMANCE-SCENARIOS.md:8-20` says thresholds
  “must be agreed ... before execution,” while PERF-01's initial criteria
  explicitly leave p99 and error limits unrecorded. The report says scenarios
  have “metrics, fixtures, and limits,” but the limits are not present.
- **Impact:** A later run can pass the throughput target while violating
  latency or reliability expectations, and threshold changes cannot be
  independently detected from Git.
- **Owner:** QA / Architecture.
- **Remediation:** Commit numeric p50/p95/p99, error, queue-age, memory, and
  drain-time limits per scenario, including measurement method and environment
  profile. Treat changes as reviewed decision-log updates.
- **Acceptance criteria:** Every PERF row has numeric pass/fail thresholds and
  units; a generated report can classify pass/fail without an out-of-band
  agreement; no production endpoint/credential gate remains bypassable.

### F-006 — Public-report claims are not linked to exact evidence (Low)

- **Evidence:** `reporting/README.md` requires each factual statement to link
  the exact Git commit and source/fixture identifiers, but
  `reporting/2026-10-30-foundation.md` only links general register paths and
  says the documents are “proven” without exact commit/fixture links.
- **Impact:** Readers cannot independently distinguish committed specification
  from executed evidence, increasing the risk of compatibility or security
  overclaiming.
- **Owner:** Public Reporting.
- **Remediation:** Add the reviewed commit SHA and per-claim requirement,
  fixture, test, or decision identifiers; keep “specified,” “implemented,” and
  “tested” labels claim-local.
- **Acceptance criteria:** A report lint/check rejects factual claims lacking
  an exact commit plus evidence identifier, and the foundation report clearly
  marks all unexecuted controls.

## Release recommendation

**FAIL** until F-001 and F-002 are fixed and covered by negative tests. F-003
through F-006 may remain deferred only if the public/API wording is narrowed
to “fixture specification” and the release gate explicitly prevents treating
the foundation as production, compatibility, or performance evidence.

