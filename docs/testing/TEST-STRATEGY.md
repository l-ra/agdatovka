# Test and conformance strategy

The test boundary is synthetic by default. Every test names its requirement,
source version/profile, fixture IDs, expected evidence, and cleanup. A green
unit test is not a compatibility result unless the matching contract and
fixture evidence are also recorded.

## Test layers

| Layer | Purpose | Required evidence |
| --- | --- | --- |
| Contract/schema | Validate `/api/v1`, problem details, pagination, idempotency, and versioning | Checked-in schema and deterministic contract report |
| Unit/property | State transitions, authorization predicates, canonical request hashing, retention clocks | Test report with seed and fixture IDs |
| Component | Database/outbox/object-store/queue behavior and restart recovery | Disposable environment logs and manifests |
| Adapter conformance | Map pinned ISDS envelopes, WSDL/XSD, auth responses, receipts, and error codes | Source-profile ID, raw synthetic payloads, normalized event report |
| Datovka smoke | Run desktop fork against AG test profile and official/reference test profile | Versioned endpoint config and screenshots/logs without secrets |
| Security/red team | Abuse authorization, trust, replay, content limits, export, logs, and recovery | Independent review task and finding disposition |
| Accessibility | Keyboard, semantics, focus, contrast, screen-reader-friendly errors | Automated scan plus manual scenario record |
| Deferred performance | Execute only in an isolated approved environment after scenario review | Load manifest, metrics, threshold decision, cleanup proof |

## Required synthetic fixture families

- `box-fo`, `box-po`, `box-ovm`, and restricted-user role fixtures using fake
  identifiers that cannot be mistaken for a real person or organization.
- Message sizes: empty/minimal, normal, boundary, large, many attachments,
  unsupported type, corrupt checksum, and resumable upload.
- Lifecycle sequences containing EV0, EV2, EV3, EV5, EV6, EV8, and EV11 from S-04,
  including login, fiction, undeliverable, weekend/holiday, and clock-skew cases.
- Receipt fixtures with valid and invalid signatures, changed bytes, expired
  certificate, unknown issuer, and unsupported source version.
- Trust fixtures from `docs/security/TRUST-MODEL.md`.
- Failure fixtures: timeout, 429, 5xx, malformed response, duplicate response,
  worker crash after side effect, object-store delay, and queue poison message.

## Acceptance gates

1. No real endpoint, credential, personal data, or production hostname is used.
2. A contract change has a versioning decision and fixture update.
3. Cross-tenant and unauthorized operations fail without leaking existence or
   content.
4. Duplicate retries do not create a second operation or untracked side effect.
5. Raw evidence, normalized projection, and audit event are mutually traceable.
6. Every failed test has a disposition; neither a skipped test nor a manual
   comment counts as evidence.

## Evidence layout

Future implementations should place deterministic output under
`evidence/<requirement-id>/<scenario-id>/` with a README containing commit,
fixture/profile versions, command, UTC timestamps, checksums, and redaction
review. CI artifacts are disposable; the manifest and decision belong in Git.
