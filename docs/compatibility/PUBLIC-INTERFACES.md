# Public-interface compatibility matrix

This matrix describes the observable compatibility target. It is not a promise
that every private behavior of ISDS or Datovka is reproduced. A row becomes
`verified` only after a synthetic fixture passes against a pinned source or
reference client. Migration is intentionally not part of the matrix.

| Area | Reference observation / source | AG Datovka 2 contract | Adapter/version rule | Evidence needed | State |
| --- | --- | --- | --- | --- | --- |
| Endpoint profile | ISDS has production and public-test environments; current portal is `datovka.gov.cz`, test is `datovka-test.gov.cz` (S-02, S-03) | Endpoint profile is named, injected, and visible in diagnostics; production profile is unavailable to tests by default | `isds-reference-2025` profile is separate from `ag-v1`; no silent hostname substitution | Profile manifest + endpoint allow-list test | Specified |
| Authentication | Portal documents password, certificate, SMS, Mobile Key, and Identita občana; external applications have their own rules (S-02, S-03) | Modern management API uses OIDC/session or scoped tokens; compatibility adapter supports only explicitly implemented ISDS mechanisms | Authentication method is advertised per profile and never downgraded | Auth matrix with positive/negative synthetic vectors | Specified |
| Client certificate trust | ISDS help describes registering a user certificate for external access (S-02) | mTLS trust store, client certificate, private key, endpoint policy, and rotation are separate configuration objects | Trust profile is versioned and pinned; key is never exported by API | Synthetic CA, expired, wrong-usage, revoked, and wrong-host tests | Specified |
| Box management | Operating rules and portal expose box/user administration concepts (S-01, S-02) | `/api/v1/boxes`, `/identities`, `/roles`, `/permissions` with explicit authorization and audit | Compatibility adapter maps only supported operations; unsupported operations return structured problem details | CRUD/deny/audit contract fixtures | Specified |
| Message composition | Datovka offers message composition and sending (S-07); ISDS rules define envelope and attachment constraints (S-02, S-06) | Draft → validate → submit operation with streamed attachments, content digests, and an idempotency key | `ag-v1` resource model is stable; ISDS adapter owns envelope mapping | Synthetic message fixtures, malformed envelope tests | Specified |
| Large messages | Current published rules describe VoDZ, `ws2`, named methods, formats, and a 50-attachment limit in a 2024 rules page (S-06) | Large payloads use object storage and resumable transfer; limits are profile metadata, not magic constants | Pin exact WSDL/rules before claiming a numeric limit | Boundary-size, checksum, resume, and rejection fixtures | Specified |
| Lifecycle | Official help defines EV0/EV2/EV3/EV5/EV6/EV8/EV11 and login/fikce semantics (S-04) | Lifecycle is an append-only event stream projected into current status; original events remain queryable | Adapter maps source event code and source version without flattening meaning | Event sequence fixtures, clock and holiday cases | Specified |
| Receipts | Datovka and ISDS help expose delivery receipts/doručenky and signed XML/ZFO exports (S-04, S-07) | Receipt is immutable evidence with raw source, digest, validation result, trace IDs, and export formats; integrity failures fail closed | Preserve raw bytes; derived PDF is not a substitute for source evidence; adapter rejects invalid signature/chain/error cases | Receipt signature/digest, fail-closed, traceability, and round-trip export tests | Verified synthetic / public approval open |
| Search | Datovka provides envelope search and local search (S-07) | Authorized, paginated search over metadata and audit indexes; content search is an explicit future capability | Search result has API version and stable cursor | Tenant isolation, pagination, Unicode/date fixtures | Specified |
| Export/import | Datovka supports ZFO, PDF, CSV/XLS-like exports and ZFO import (S-07, S-04) | Export is a job with manifest, checksums, authorization, and audit; import is only synthetic fixture ingestion in this project | Never call fixture import migration | Export manifest and tamper test | Specified |
| Errors | Modern HTTP semantics and problem details (S-09, S-10) | JSON `application/problem+json`, stable `type` and `code`, request ID, retryability, and field errors | Existing adapter errors map to stable codes; raw upstream detail is redacted and retained in evidence | Contract tests for 4xx/5xx/retry behavior | Specified |
| Retention | Published help describes 90-day and 100-day reference behavior and Datový trezor (S-05) | Tenant policy, legal hold, deletion job, tombstone, and evidence retention are separate | Reference profile values are configurable and source-versioned | Clock/holiday/deletion fixtures | Specified |
| CLI/desktop workflow | Datovka advertises command-line and records-service APIs plus local DB workflows (S-07) | Desktop fork uses endpoint profiles; CLI compatibility is a separate adapter, not a server-side promise | No direct dependency on former AGDatovka code | Fork smoke test on synthetic profile | Planned |

## Compatibility invariants

1. A public field or state is not renamed or reinterpreted in-place. Add a new
   API version or adapter mapping and record the decision.
2. Every outbound request carries a correlation ID and source-profile ID; every
   retry carries the same idempotency key and a new attempt number.
3. Raw upstream envelopes, receipts, and error codes are retained as evidence
   when policy permits; normalized projections never overwrite them.
4. The compatibility target is the public interface/workflow behavior needed
   after a future migration. No migration code, source database, or historical
   data is imported here.
