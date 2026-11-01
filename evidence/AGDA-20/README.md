# AGDA-20 Phase 3 candidate evidence

This directory contains repository evidence for the synthetic functional
reliability vertical slice. It is a candidate implementation record, not a
release verdict.

## Evidence map

| Concern | Source/test evidence | Disposition |
| --- | --- | --- |
| F-003 idempotency race | `ag_datovka/app.py`; `tests/test_management_api.py` concurrency and crash-recovery tests | Implemented and deterministic in the local SQLite fixture |
| F-004 malformed attachment length | `ag_datovka/app.py::_declared_length`; `tests/test_qa_conformance.py` | Stable Problem responses in synthetic boundary |
| F-005 byte/digest binding | `ag_datovka/app.py::_attachment_input`; attachment integrity tests | Server-computed digest and stored bytes; no metadata-only path |
| Async send | `ManagementApp.run_worker`; management worker test | Synthetic outbox/lease/lifecycle projection |
| Receipts | `receipts` table and receipt API route | Immutable synthetic raw evidence |
| Retention/restore | `/retention/*` routes, `fixtures/retention/policy.json`, `docs/requirements/AGDA-26-LEGAL-TRACEABILITY.md`, and management regression tests | Synthetic versioned policy, deletion job/tombstone/digest, manifest export, isolated restore report, and tamper fail-closed checks |
| Management UI | `ui/index.html`, `ui/app.js`, `ui/styles.css` | Static accessible vertical slice; audit still pending |
| Performance | `docs/testing/PERFORMANCE-SCENARIOS.md` | Defined, not run; human approval required |
| Fork workflow | `fork/` and `docs/testing/CZNIC-DATOVKA.md` | Offline foundation; local endpoint run pending |
| Independent review/release | AGDA-31/AGDA-32 | Pending specialist evidence; no completion claim |

## Reproduction

```text
python3 -m py_compile ag_datovka/app.py
python3 -m unittest discover -s tests -v
```

The latest candidate result recorded 42 passing tests. It must be reproduced
from the exact Git commit carrying this directory; timestamps and random
resource IDs are not evidence of external delivery.
