# Management API contract — v1 baseline

This is the modern, versioned management contract. It is deliberately separate
from an ISDS SOAP/WSDL contract; the compatibility adapter owns that mapping.
The local dependency-free foundation implements this contract for synthetic
fixtures. It is not a production deployment, ISDS SOAP implementation, or
migration path. See `docs/compatibility/PUBLIC-INTERFACES.md` for the reference
behavior matrix and `docs/management/openapi.v1.json` for the machine-readable
schema.

## Contract rules

- Base path: `/api/v1`; JSON uses UTF-8 and RFC 3339 timestamps in UTC.
- Every response includes `requestId`; every mutating request accepts a caller
  `Idempotency-Key` and a `Correlation-Id`.
- Message/attachment bytes are uploaded as streams or by a bounded synthetic
  `contentBase64` fixture. The server computes the digest and byte length from
  received bytes; metadata-only attachment requests are rejected. Metadata
  never contains an unbounded byte field.
- Long operations return `202 Accepted` with an operation resource. HTTP
  acceptance is not upstream delivery.
- Errors use `application/problem+json` (RFC 9457) with stable `type`, `code`,
  `title`, `status`, `detail` safe for the caller, `requestId`, `retryable`, and
  optional `fieldErrors`. Upstream credentials and raw sensitive payloads are
  never returned.
- All list endpoints use a stable opaque cursor and a bounded `limit`; clients
  must not rely on database ordering.

## Resources and endpoints

| Method and path | Purpose | Success | Permission examples |
| --- | --- | --- | --- |
| `POST /boxes` | Create a databox in the AG control plane | `201` box | `box:create` |
| `GET/PATCH /boxes/{boxId}` | Read/update non-secret box configuration | `200` box | `box:read`, `box:update` |
| `POST /boxes/{boxId}/identities` | Add an identity binding | `201` identity | `identity:manage` |
| `GET/PATCH/DELETE /identities/{id}` | Manage identity metadata/status | `200/204` | `identity:manage` |
| `POST /roles`, `POST /permissions` | Define platform-global roles and permissions | `201` | platform control-plane authorization |
| `PUT /boxes/{boxId}/members/{identityId}` | Assign role(s) within a box | `200` membership | `membership:manage` |
| `POST /auth-methods` | Register an allowed auth method/profile, never a raw secret | `201` | `auth:manage` |
| `POST /messages` | Create a message draft with metadata and content references | `201` draft | `message:create` |
| `POST /messages/{id}/attachments` | Stream an attachment or submit a bounded synthetic byte fixture | `201/202` verified content ref | `message:create` |
| `POST /messages/{id}/submit` | Validate and enqueue delivery | `202` operation | `message:send` |
| `GET /messages/{id}` | Read authorized normalized message projection | `200` message | `message:read` |
| `GET /messages/{id}/events` | Read lifecycle events and source codes | `200` page | `message:read` |
| `GET /messages/{id}/receipts/{receiptId}` | Read immutable receipt evidence metadata | `200` receipt | `receipt:read` |
| `POST /operations/{id}/cancel` | Request cancellation before irreversible submission | `202` operation | `operation:cancel` |
| `GET /operations/{id}` | Observe async state, attempts, and retryability | `200` operation | `operation:read` |
| `GET /messages/search` | Search authorized envelope/audit metadata | `200` page | `message:read` |
| `POST /exports` | Create a manifest/checksummed export job | `202` export job | `export:create` |
| `GET /exports/{id}` | Observe/download an authorized export | `200/202` | `export:read` |
| `GET /audit/events` | Query append-only audit projections | `200` page | `audit:read` |

## Canonical message state model

```text
draft -> validated -> accepted -> queued -> submitting -> submitted
                                             |              |
                                             |              +-> delivered
                                             |              +-> delivered_by_login
                                             |              +-> delivered_by_fiction
                                             |              +-> undeliverable
                                             +-> retry_wait -> submitting
validated/queued -> rejected
any pre-terminal state -> cancelled (only when policy allows)
submitted -> failed_terminal (only with source evidence)
```

The current status is a projection. Events are authoritative and include
`eventType`, source event code, source profile/version, `occurredAt`,
`recordedAt`, actor/system, attempt, reason, and previous-event digest.
Implementations must not turn a transient `submitted` or `queued` state into a
delivery claim.

## Example submit request

```http
POST /api/v1/messages/msg_01J.../submit
Authorization: Bearer <scoped-token>
Idempotency-Key: submit-msg_01J-v1
Correlation-Id: req-01J...
Content-Type: application/json

{"targetBoxId":"box_test_recipient","profile":"isds-reference-2025",
 "deliveryMode":"standard","contentDigest":"sha256:..."}
```

```json
{
  "operationId": "op_01J...",
  "messageId": "msg_01J...",
  "status": "queued",
  "acceptedAt": "2026-10-30T12:00:00Z",
  "requestId": "req-01J..."
}
```

The same key and semantically identical body return the original operation;
the same key with a different body returns `409 idempotency_conflict`.
The management boundary durably claims `(tenant, actor, key)` before routing.
Claims record attempt count and `claimed`/`completed` response state; a retry
after a synthetic timeout or crash reclaims the same row and never exposes a
database uniqueness error. This SQLite behavior is a deterministic local
fixture, not production database evidence.

### Verified attachment ingress

The local direct-call fixture accepts JSON with `filename`, optional
`mediaType`, `contentBase64`, and optional declared `byteLength` and
`contentDigest`. It decodes the bytes, computes `sha256:<hex>`, and compares
any declarations before persisting the content reference. Missing bytes,
malformed lengths, digest mismatches, negative lengths, and over-limit lengths
return stable Problem JSON.

The WSGI boundary accepts an octet-stream body with `X-Upload-Filename`,
optional `X-Upload-Media-Type`, `X-Content-Length`, and `X-Content-Digest`
headers. The server remains authoritative for the recorded digest and length.

### Synthetic worker and receipts

Submit creates the operation projection and durable outbox item in one request
transaction and returns `queued`. The explicit local `ManagementApp.run_worker()`
seam dispatches tenant-scoped leases through the synthetic adapter, persists a
stable per-attempt reconciliation key, projects `submitting` and `delivered`
lifecycle events, and persists an immutable receipt with raw evidence digest.
It never contacts a public or production endpoint. A `delivered` projection is
therefore synthetic worker evidence, not a legal or production delivery claim.
The receipt response preserves `rawXml` and additive `rawEvidenceBase64` fields,
rechecks the stored bytes against `rawDigest`, and returns `validation`,
`eventId`, and `auditEventId` trace links. A digest mismatch or mutable marker
returns `409 receipt_integrity_failure`; it never serves unverified evidence.
Exports embed the same receipt record and digest, so the receipt, operation,
lifecycle event, audit record, and export manifest remain mutually traceable.

### Retention and restore controls

`POST /retention/legal-holds`, `PATCH /retention/legal-holds/{id}`, and
`POST /retention/deletion-requests` provide explicit synthetic policy,
legal-hold, and tombstone evidence. `POST /retention/restore` verifies an
export manifest, attachment digests, audit hash chain, authorization scope,
and pending-operation reconciliation in a disposable namespace; it never
blindly replays a send. The policy version is `ag-v1` and is a reference
fixture, not universal legal advice.

## Authorization model

Permissions are scoped to a tenant/box and evaluated after authentication:

| Role example | Allowed | Explicitly not implied |
| --- | --- | --- |
| `box-owner` | Box config, membership, message read/send | Global policy, trust-root administration, or platform administration |
| `box-operator` | Compose/send/read messages and receipts | Membership changes, exports outside scope |
| `auditor` | Read audit, lifecycle, receipts, and approved exports | Send, delete, or change policy |
| `trust-admin` | Tenant-scoped trust/key metadata where explicitly exposed | Global policy, trust-root administration, or grant message permissions |
| `platform-admin` | Platform-wide operations with separate break-glass audit | Routine tenant impersonation |

Every allow/deny decision records subject, tenant, resource, action, policy
version, and reason. A certificate or upstream account is not itself an AG
role.

Global roles, permissions, trust profiles, and endpoint profiles are managed
only by the platform control plane. Every tenant resource boundary re-checks
the authenticated tenant and permission; caller-supplied tenant identifiers
do not widen scope. Identity references in authentication methods and message
senders must belong to the same box, otherwise the request fails with
`cross_tenant_reference`.

## Audit events

Minimum event families: `box.created`, `box.configured`, `identity.changed`,
`membership.changed`, `auth_method.changed`, `trust_profile.changed`,
`message.created`, `content.attached`, `operation.accepted`, `operation.attempted`,
`upstream.event.received`, `receipt.validated`, `export.created`,
`retention.deleted`, `legal_hold.changed`, `authorization.denied`.

Audit records are append-only, hash-linked per tenant/stream, exportable with a
manifest, and retained under the policy in `docs/data/DATA-FLOW-RETENTION.md`.

## Compatibility and deprecation

- `/api/v1` is additive-only once published. A semantic change requires `/api/v2`
  or a new named adapter profile.
- Upstream WSDL names/codes stay in adapter evidence and are mapped to stable
  domain codes; unsupported operations return `501 not_supported`, not a
  fabricated success.
- Deprecation requires a replacement, migration-free client guidance, fixture
  coverage, and a decision-log entry. It must not imply data migration.
