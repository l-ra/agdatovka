# AGDA-30 — QA conformance report and performance disposition

## Scope and disposition

This is a synthetic-only QA record for the Phase 3 candidate. Functional and
local end-to-end conformance passed. PERF-01 through PERF-10 were not executed:
the repository has no approved isolated load environment or recorded human
approval for synthetic measurement. This is an explicit deferral, not a
performance pass or production-readiness claim.

## Reproduction

From the repository root:

```text
python3 -m py_compile ag_datovka/*.py qa/*.py fork/scripts/*.py
python3 -m unittest discover -s tests -v
python3 -m qa.performance_readiness --validate
fork/scripts/check.sh
python3 fork/scripts/local_workflow.py --manifest /tmp/agda-30-local-workflow.json
```

The deterministic suite result for this record was **57 tests passed**. The
readiness validator is validation-only and performs no network or load I/O.
The fork workflow uses an in-process disposable fixture and is not external
Datovka or ISDS interoperability evidence.

## Traceability

| Area | Evidence | Result |
| --- | --- | --- |
| Fixture profile and deterministic seed | `qa/fixtures.json` | `synthetic-ag-v1-2026-10-30`, seed `20261030` |
| API/content boundaries | `tests/test_qa_conformance.py` | Pass: metadata-only, length, digest, 16 MiB boundary, octet-stream, WSGI malformed lengths |
| Reliability/security regression | `tests/test_management_api.py`, `tests/test_pipeline.py`, `tests/test_observability_security.py`, `tests/test_security_boundary.py` | Pass in full suite |
| Adapter/lifecycle compatibility | `tests/test_isds_adapter.py`, `fixtures/isds/` | Pass in full suite; synthetic profile only |
| UI/accessibility source conformance | `tests/test_ui_accessibility.py`, `evidence/AGDA-28/README.md` | Pass in full suite; no certification claim |
| Local fork workflow | `evidence/AGDA-29/run-manifest.json` | Pass; in-process synthetic fixture |
| Performance readiness | `qa/performance-scenarios.json`, `qa/performance-harness.json` | Validation pass; no load execution |

## Performance decision

Numeric threshold proposals are recorded in
`docs/testing/PERFORMANCE-THRESHOLDS.json` and
`docs/testing/PERFORMANCE-THRESHOLD-DECISION-LOG.md`. They are QA proposals,
not an approval to run. Architecture approval and an isolated synthetic/
loopback environment must be recorded before any PERF scenario is executed.

The required future manifest remains PERF-01..PERF-10 with commit, profile,
seed, request/operation counts, latency histograms, queue/resource metrics,
checksums, cleanup proof, and abort-condition evidence. The performance
manifest explicitly forbids production DNS, credentials, and real content.

## Signed QA deferral

**Signer:** QA Conformance Engineer (AGDA-30)

**Decision:** Defer all performance execution. Do not report p99, error,
drain, memory, retry, or telemetry measurements from this run. Readiness
artifacts are scenario definitions only. The functional suite and local
synthetic workflow may be used as candidate evidence subject to AGDA-31 and
AGDA-32 review gates.

**Reason:** No human-approved execution authorization and no approved isolated
measurement environment are present in the issue or repository at this
heartbeat. This preserves the synthetic-only and no-production-load boundary.

**Evidence commit:** The exact Git commit for this record is supplied in the
AGDA-30 Paperclip handoff comment together with the reproduced commands and
results.
