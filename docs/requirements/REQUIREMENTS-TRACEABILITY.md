# Requirements and traceability

Status: baseline requirements for implementation planning. `Specified` means
the contract exists in this repository; it does not mean the feature is
implemented or legally approved.

| ID | Requirement | Source(s) | Acceptance evidence | Owner / next slice | State |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | The system is a standalone implementation with no dependency on, code import from, credential reuse with, or continuity claim to the former AGDatovka implementation. | Project scope; BOUNDARIES | Dependency scan, clean test fixtures, architecture review | Architecture | Specified |
| REQ-002 | An authorized operator can create/configure a databox, identities, roles, permissions, and authentication methods. | S-01, S-02, S-07 | API contract tests for allowed/denied operations and audit records | Backend Management | Specified |
| REQ-003 | A sender can create, validate, submit, and retry a message with attachments without loading the full payload into API memory. | S-06, S-07, S-09 | Streaming fixture with checksums, bounded memory, and failed-upload recovery | Messaging | Specified |
| REQ-004 | Message lifecycle and delivery evidence distinguish submitted, delivered, read/login, statutory fiction, failed, and undeliverable outcomes. | S-01, S-04, S-07 | EV fixture set and deterministic state-machine tests | ISDS Interoperability / QA | Specified |
| REQ-005 | Receipts and message evidence can be retrieved and exported without altering the original evidence. | S-04, S-07 | Immutable receipt fixture; ZFO/XML and PDF/CSV export tests where supported | Messaging / QA | Specified |
| REQ-006 | Users can search message metadata and audit metadata with authorization and pagination. | S-07, S-09, S-14 | Query contract, tenant-isolation tests, stable cursor pagination | Backend / QA | Specified |
| REQ-007 | Security-sensitive actions and lifecycle changes produce append-only audit events with actor, authorization context, request ID, time, event version, and content digest. | S-01, S-13, S-14 | Tamper-evidence and export/replay tests | Security / Backend | Specified |
| REQ-008 | Trust configuration has explicit certificate, key, chain, revocation, endpoint, and rotation boundaries. | S-02, S-11, S-12, S-15 | Synthetic CA/leaf vectors, negative trust tests, rotation/revocation evidence | Security/Trust | Specified |
| REQ-009 | A versioned management API coexists with a compatibility adapter; no public contract change is silent. | S-07, S-08, S-09, S-10 | OpenAPI/contract fixture, version-negotiation and deprecation tests | Backend / Compatibility | Specified |
| REQ-010 | Asynchronous work supports idempotency, durable retries, queue backpressure, dead-letter handling, and operator-visible status. | Target architecture; S-09 | Fault-injection tests and operation replay report | Messaging / QA | Specified |
| REQ-011 | The architecture has a verified future scenario for at least 1,000 messages/minute and large messages; performance execution is deferred. | Product scope; S-06 | Scenarios, fixtures, metrics, thresholds, and a no-production-load gate | QA / Architecture | Specified |
| REQ-012 | Compatibility testing uses synthetic accounts, certificates, trust stores, endpoints, and messages only. | S-03 | Fixture manifest and secret scan; no real-data test path | QA / Compatibility | Specified |
| REQ-013 | A documented Datovka desktop fork can run against the new implementation and the official/reference test system using switchable endpoint profiles. | S-07, S-08, S-16 | Reproducible build/run guide and smoke-test evidence | CZ.NIC Compatibility | Specified |
| REQ-014 | Retention rules are explicit, configurable, auditable, and distinguish reference-server behavior from archive/legal-hold policy. | S-05, S-14 | Clock/holiday tests, deletion/tombstone evidence, policy matrix | Data / Legal | Specified |
| REQ-015 | Public reports state verified progress, limitations, and risks without secrets, personal data, unpublished vulnerabilities, or unsupported compliance claims. | Project reporting policy | Report lint/redaction review and source links | Public Reporting | Specified |

## Traceability rules

- Every implementation issue references one or more requirement IDs and names
  the fixture or evidence path it will add.
- A requirement is complete only when its contract, test, evidence, and review
  state are all recorded. A prose claim or Paperclip comment is not evidence.
- If an official source changes, open a compatibility decision, update the
  source register, and rerun affected fixtures before changing behavior.
