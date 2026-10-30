# System boundaries and target architecture

AG Datovka 2 is a standalone reimplementation. It has no code, database,
credentials, or runtime dependency on the former AGDatovka implementation.
Migration of existing databoxes and historical data is a separate project.
This project defines and tests the public contracts and observable workflows
that a later migration must preserve.

## Component view

```text
management UI / CLI / Datovka fork
              |
       API gateway + authn
              |
  versioned management API (v1)
     |       |          |
  policy  metadata   operation API
     |       |          |
     |  relational DB  outbox -> durable queue -> workers
     |       |                              |
     |       +---- audit/event log         adapter profiles
     |                                      |       |
  object store <---- streamed content      |    ISDS test/reference
                                           +---- future providers

observability: metrics + traces + structured redacted logs + evidence manifests
trust: public TLS | management auth | adapter mTLS | signing/timestamp service
```

## Hard boundaries

- **Management/API boundary:** Authenticated callers receive a versioned
  resource model. They do not receive database rows or upstream SOAP objects.
- **Content boundary:** The API streams content to object storage. Workers read
  by digest/reference; no component assumes an attachment fits in memory.
- **Adapter boundary:** The adapter owns WSDL/envelope/auth/trust peculiarities
  and maps them to domain events. The core never embeds production endpoints.
- **Trust boundary:** Public TLS, caller authentication, outbound mTLS, trust
  anchors, private keys, and authorization policy are separate controls.
- **Evidence boundary:** Raw envelopes/receipts and immutable audit events are
  write-once from application code. Projections and indexes are rebuildable.
- **Data boundary:** All tests use synthetic identities, certificates, and
  content. Production access is a future separately approved environment.

## Target load assumptions

- Baseline target: 1,000 accepted messages/minute (16.7/s), with a separately
  declared burst profile and large-message distribution; see
  `docs/testing/PERFORMANCE-SCENARIOS.md`.
- API admission is decoupled from upstream delivery. Queue depth, age, retry
  rate, object-store latency, and upstream response classes are observable.
- Workers scale horizontally by partition/tenant/profile. Idempotency records
  and leases prevent duplicate side effects when workers restart.
- Backpressure is explicit: bounded upload concurrency, queue quotas, per-tenant
  limits, and `429`/`Retry-After` or an accepted asynchronous operation when
  capacity is unavailable.
- A message is not reported as delivered until the adapter records a source
  delivery event or an explicit terminal failure. HTTP acceptance is not delivery.

## Failure and recovery invariants

1. An outbox record is committed with the operation before a worker is allowed
   to submit it.
2. Every attempt has a stable operation/idempotency key, a monotonic attempt
   number, and a reason for retry or terminal failure.
3. A worker lease can expire safely; a resumed worker rechecks the idempotency
   record before performing an external side effect.
4. Recovery restores metadata, content manifests, event order, and trust
   configuration checksums before traffic is enabled.
