# Phase 3 implementation — synthetic functional reliability and compatibility slice

Status: candidate synthetic/test milestone. This document records implemented
repository evidence and does not authorize production use, public-test access,
legal-compliance claims, migration, or continuity with the former AGDatovka
implementation.

## Baseline and task tree

The implementation starts from the Phase 2 source baseline
`dce9120b634397d4811c15d6ba033674e5dc9c63`. The authorized Paperclip child
tasks are materialized as AGDA-21 through AGDA-32:

| Phase task | Paperclip issue | Owner role | Gate |
| --- | --- | --- | --- |
| P3-01 evidence/contract reconciliation | AGDA-21 | Release Integration | prerequisite |
| P3-02 atomic idempotency | AGDA-22 | Backend Messaging | F-003 closure |
| P3-03 verified content ingress | AGDA-23 | Backend Messaging | F-004/F-005 closure |
| P3-04 worker/reconciliation/backpressure | AGDA-24 | Backend Messaging | durable synthetic delivery |
| P3-05 lifecycle/receipt evidence | AGDA-25 | ISDS Interoperability | adapter evidence |
| P3-06 retention/restore | AGDA-26 | Requirements and Legal | policy/restore gate |
| P3-07 observability/security | AGDA-27 | Security Trust | redaction/threat gate |
| P3-08 management UI | AGDA-28 | Backend + QA accessibility | accessible API client |
| P3-09 Datovka fork workflow | AGDA-29 | CZ.NIC Compatibility | local fork gate |
| P3-10 conformance/measurement | AGDA-30 | QA Conformance | performance approval gate |
| P3-11 independent re-review | AGDA-31 | Independent Red Team | release verdict |
| P3-12 integration/mirror/report | AGDA-32 | Release Integration | final release gate |

The Paperclip dependency edges are authoritative for execution order. This
Git record is the durable description of what the repository implements and
what remains pending.

## Implemented in this candidate

- `ag_datovka/app.py` serializes the local SQLite request critical section and
  handles a uniqueness race as an idempotent replay or stable conflict. The
  concurrent regression sends 100 same-key requests and observes one box and
  one durable response.
- Attachment ingress requires received bytes. JSON fixtures use bounded
  `contentBase64`; the WSGI path accepts octet-stream bytes. The server
  computes the SHA-256 digest and byte length, verifies optional declarations,
  rejects metadata-only and malformed/negative/non-finite/oversized lengths,
  and stores the verified content bytes in the synthetic fixture boundary.
- Submit creates an outbox item. `ManagementApp.run_worker()` is an explicit
  synthetic adapter seam with dispatch, leases, attempts, retry/dead-letter
  outcomes, lifecycle projection, and immutable receipt evidence. It has no
  network or upstream credentials.
- Receipt retrieval now returns raw synthetic evidence, source code/profile,
  digest, validation time, and immutable marker. The receipt is linked to the
  operation, message event chain, export, and audit hash chain.
- Exports include messages, verified attachment manifests, operations,
  receipts, audit events, and policy version. Retention endpoints implement
  legal holds, release, tombstone deletion requests, and isolated synthetic
  restore verification with an explicit no-blind-send-replay check.
- `ui/` contains a dependency-free keyboard-accessible management UI for
  boxes, message/attachment submission, operations, search, export/audit
  inspection, and redacted error display. It uses only `/api/v1`.

## Verification

Run from the repository root:

```text
python3 -m py_compile ag_datovka/app.py
python3 -m unittest discover -s tests -v
```

The candidate run recorded 42 passing deterministic tests. The test suite
covers the old Phase 2 boundaries plus:

- 100-request same-key idempotency concurrency;
- metadata-only rejection, digest/length mismatch, boundary-size content,
  and octet-stream handling;
- queued submit → synthetic worker → delivered projection → receipt retrieval;
- legal-hold deletion blocking, tombstone evidence, and restore verification.

## Explicitly unmeasured or pending

- The 1,000 messages/minute and large-message scenarios remain defined but not
  executed. No human-approved thresholds or load environment are recorded in
  this repository, so P3-10 must defer the load portion rather than call it a
  pass.
- The worker is synthetic and local. It does not prove external ISDS delivery,
  HA, crash recovery across processes, or legal delivery/fikce semantics.
- The Datovka fork has offline fixtures and an endpoint profile, but this
  candidate does not claim a completed desktop build against a live local
  endpoint until P3-09 records that workflow.
- The UI is a static vertical slice; no accessibility audit beyond source and
  deterministic fixture coverage is claimed until P3-08 completes.
- Independent security re-review, local no-fast-forward integration, exact
  mirror verification, and sanitized public milestone publication remain P3-11
  and P3-12 gates. No mirror URL or SHA is invented here.

## Safety boundary

All fixtures, endpoints, certificates, tokens, message bodies, and restore
namespaces used by this candidate are synthetic. Production deployment, real
data, public-test accounts, production credentials, migration, qualified
signatures/timestamps, and compliance certification remain out of scope.
