# AGDA-13 performance readiness evidence

## Disposition

This evidence records executable scenario readiness, not measured performance.
No production endpoint, credential, real message content, or production load
test was used. The exact Git commit containing this record is the handoff
commit for AGDA-13.

## Reproduction

From the repository root:

```text
python -m qa.performance_readiness --validate
python -m unittest tests.test_qa_conformance tests.test_performance_readiness
```

The validator performs local JSON/profile checks only and has no network or
load-generation path.

## Traceability

| Artifact | Purpose |
| --- | --- |
| `qa/performance-scenarios.json` | Versioned scenarios PERF-01..PERF-10, fixtures, metrics, limits, sampling, resource assumptions, SLO hypotheses, and abort thresholds |
| `qa/performance-harness.json` | Future-run harness contract and explicit validation-only gate |
| `qa/performance_readiness.py` | Deterministic local validator; does not execute load |
| `qa/fixtures.json` | Synthetic profile and deterministic seed `20261030` |
| `docs/testing/PERFORMANCE-SCENARIOS.md` | Human-readable scenario summary |
| `docs/testing/PERFORMANCE-THRESHOLDS.json` | Numeric QA proposal with explicit deferred execution gate |
| `docs/testing/PERFORMANCE-THRESHOLD-DECISION-LOG.md` | QA threshold proposal, rationale, approval state, and abort conditions |

## Acceptance record

- Scenario coverage: sustained 1,000 messages/minute, burst/drain,
  large/resumable content, idempotency, retries/faults, worker failure,
  backpressure, horizontal scaling, observability, retention/evidence, and
  recovery/cleanup are represented.
- Determinism: fixture profile and seed are cross-checked by the validator.
- Safety: production DNS, credentials, and real content are explicitly
  forbidden; abort thresholds include endpoint, secret, leak, tenant, queue,
  memory, and evidence-accounting failures.
- Evidence contract: a future measured run must retain commit, manifest digest,
  seed, counts, latency histograms, queue/resource metrics, checksums, and
  cleanup proof.
- SLO hypotheses: accepted rate must sustain at least 1,000/minute; lost and
  duplicate operations are zero; the QA proposal is p99 admission latency
  ≤750ms, unexpected error rate ≤1%, queue drain ≤15 minutes, worker memory
  ≤512MiB, retry attempts ≤5 per operation, and telemetry CPU overhead ≤15%
  with zero dropped required events. These values remain unapproved until
  Architecture records its decision before an approved run.
- Result today: readiness validation passed; performance execution is
  intentionally deferred and no performance result is asserted.
