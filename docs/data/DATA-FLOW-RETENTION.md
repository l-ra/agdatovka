# Data-flow and retention model

The service handles messages, identities, certificates, receipts, and audit
evidence that may contain personal or legally sensitive information. The model
minimizes data, separates content from metadata, and makes deletion observable.

## Flow

```text
caller -> authenticate/authorize -> create metadata draft
                                  -> stream content -> digest/object manifest
                                  -> validate -> transactional outbox
                                  -> queue -> adapter worker
                                  -> named test/reference endpoint
                                  <- receipt/envelope/event
                                  -> immutable raw evidence + projection/index
                                  -> authorized search/export
```

At every hop, record tenant, subject/service, correlation ID, operation ID,
profile version, content digest, and time. Logs contain identifiers and outcome
codes only; message bodies, credentials, private keys, and full personal data
are excluded by default.

## Data classes

| Class | Examples | Primary store | Default access |
| --- | --- | --- | --- |
| Identity/policy | subject, box ID, role, permission, auth method metadata | Transactional metadata DB | Policy-scoped operators |
| Message metadata | sender/recipient identifiers, subject, timestamps, state | Metadata DB and indexes | Message permissions |
| Message content | body/attachments, raw envelope | Content object store | Message permission + export policy |
| Evidence | raw receipt/envelope, validation result, digests, timestamps | Immutable evidence store | Auditor/security/legal hold |
| Audit | actor, action, policy version, outcome, object digest | Append-only event store | Auditors/security |
| Secrets | private keys, credentials, refresh tokens | External secret store/HSM | Narrow adapter/service identity |
| Telemetry | latency, queue age, status/error code, redacted trace fields | Observability system | Operators; time-limited |

## Retention policy model

Retention is evaluated by policy version and recorded in the audit stream. The
following values are a compatibility profile derived from published ISDS help,
not a universal legal policy:

| Data | Compatibility profile | AG policy requirement |
| --- | --- | --- |
| Ordinary reference-server message | Eligible for deletion 90 days after delivery by login, unless the reference service's current rules say otherwise | Tenant/archive policy must choose a period and disclose it |
| System reference-server message | Published help describes deletion 100 days from delivery and no Datový trezor storage | Model as a distinct message class; verify current rules before use |
| Fikce/delivery evidence | Never infer deletion from message content retention | Retain enough event/digest evidence for the approved legal/evidence policy |
| Archived content | Not part of the default reference-server lifecycle | Separate archive class with owner, purpose, legal hold, and expiry |
| Audit/evidence | Append-only and hash-linked | Retention period and legal hold require operator/legal decision |
| Backups | Encrypted copies with expiry metadata | Deletion policy must cover backup expiry and restore replay |
| Secrets | Rotation and revocation lifecycle | Never include in ordinary content backups or exports |

Deletion is a job, not an ad-hoc SQL command: select eligible object, recheck
legal hold and policy version, write `retention.deletion_requested`, delete or
tombstone content, write `retention.deleted` with digest and reason, and verify
that indexes/replicas/backups follow their documented policy. A tombstone must
not make deleted content recoverable through the API.

## Export and restore

Exports include a manifest, policy snapshot, object digests, event range, and
redaction mode. Restore first creates an isolated staging namespace, verifies
checksums and event hash links, reapplies retention/legal holds, and runs
authorization and trust checks before any content becomes queryable.

There is no migration path in this project. A synthetic fixture import is only a
test tool and must be labeled `fixture-import`, never `migration`.
