# Architecture and decision log

Decisions are recorded before implementation makes them expensive to change.
Status values: `accepted` means the baseline direction is approved for the
next implementation slice; `pending` means a legal, security, or source
decision is still required.

## ADR-001 — Standalone boundary

- **Status:** accepted
- **Decision:** Build a new service, contracts, fixtures, and fork workflow in
  this repository. Do not import, link, copy runtime data from, or claim
  continuity with the former AGDatovka implementation.
- **Why:** The product is an independent reimplementation. Migration is a
  separate project and must not silently shape the runtime boundary.
- **Evidence:** `docs/architecture/BOUNDARIES.md`, REQ-001.

## ADR-002 — Ports and adapters for public compatibility

- **Status:** accepted
- **Decision:** Keep the versioned management API and domain model independent
  from ISDS SOAP/WSDL and Datovka local storage. Implement each upstream or
  desktop integration behind a versioned adapter and profile.
- **Why:** Upstream rules and client libraries evolve independently; adapters
  allow conformance fixtures without coupling the core service to one client.
- **Rejected:** Making the internal data model equal to a WSDL schema.

## ADR-003 — Event-backed lifecycle and immutable evidence

- **Status:** accepted
- **Decision:** Store append-only lifecycle/audit events and derive current
  projections. Preserve raw receipts/envelopes and their digests.
- **Why:** Delivery, retry, receipt validation, and legal evidence need the
  original sequence, not just the latest status.
- **Rejected:** Updating one mutable message row and discarding transitions.

## ADR-004 — Metadata database plus content object store

- **Status:** accepted
- **Decision:** Keep identities, metadata, permissions, indexes, operations,
  events, and manifests in a transactional database. Stream message/attachment
  content to content-addressed object storage with checksums.
- **Why:** Large messages must not consume API/worker memory; metadata queries
  and content retention have different scaling and policy needs.
- **Rejected:** Storing arbitrary attachment bytes in the request database.

## ADR-005 — Durable asynchronous send pipeline

- **Status:** accepted
- **Decision:** API accepts a validated operation, commits an outbox event, and
  queues work for horizontally scalable workers. Retries are bounded and
  idempotent; poison work goes to a reviewable dead-letter queue.
- **Why:** External endpoints, large uploads, backpressure, and retries make a
  synchronous request unsafe at the target load.
- **Rejected:** Retrying inside the HTTP request until upstream succeeds.

## ADR-006 — Explicit API versioning

- **Status:** accepted
- **Decision:** Expose `/api/v1` for modern contracts and retain compatibility
  adapters under an explicit profile/version namespace. Additive changes are
  allowed within a version; semantic changes require a new version or adapter.
- **Why:** Public compatibility and modernization are both requirements.

## ADR-007 — Trust/key separation

- **Status:** accepted
- **Decision:** Store trust anchors and endpoint policy separately from private
  keys and from application authorization. A certificate identifies a key
  binding; it does not grant domain permissions by itself.
- **Why:** Certificate rotation, revocation, mTLS, and tenant permissions must
  be auditable independently.
- **Rejected:** One global trust store and one shared client key.

## ADR-008 — Synthetic-first evidence

- **Status:** accepted
- **Decision:** Use synthetic accounts, certificates, endpoints, and fixtures;
  default CI cannot address production domains. Performance execution is
  deferred, but scenarios and acceptance limits are committed now.
- **Why:** Protects users and makes evidence reproducible.

## ADR-009 — Retention policy is configuration, not a hard-coded promise

- **Status:** accepted
- **Decision:** Model reference-server retention, tenant archive policy, legal
  hold, backup expiration, and audit retention separately. A reference profile
  may reproduce a published ISDS behavior such as 90 days after delivery by
  login, but it is not a universal legal rule.
- **Why:** The published behavior, operator policy, and legal duty are distinct
  sources of truth.

## Pending decisions

- **ADR-P01:** Exact current ISDS WSDL/XSD/rules snapshot and supported methods.
- **ADR-P02:** Operator/controller/processor roles and retention schedule.
- **ADR-P03:** Qualified trust-service/timestamp provider and evidence format.
- **ADR-P04:** Deployment platform, database/object-store technology, and queue
  implementation; these are intentionally not fixed by this foundation.

## ADR-010 — Phase 2 evidence reconciliation and synthetic contract freeze

- **Status:** accepted
- **Decision:** Freeze Phase 2 as synthetic/test-only evidence. Use the exact
  local source and integrated-main SHAs in the AGDA-21 reconciliation record;
  preserve the AGDA-16 failed mirror attempt as historical evidence; and do
  not treat readiness manifests, offline fixtures, or the 33-test report as
  production, compatibility, performance, security, legal, or compliance
  proof.
- **Conflicts resolved:** The AGDA-16 `/tmp/agda-10-integration` narrative is
  historical rather than the current checkout; the provider refs are
  divergent and do not establish full mirror parity; AGDA-14's 29-test text
  is superseded by the current 33-test run without changing its adverse
  verdict; and AGDA-13 readiness remains distinct from deferred performance
  execution.
- **Evidence:** `evidence/AGDA-21/README.md`, `evidence/AGDA-14/README.md`,
  `evidence/AGDA-13/README.md`, and `main:evidence/AGDA-16/mirror-verification.md`.
