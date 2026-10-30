# Deferred performance scenarios

Performance execution is intentionally deferred. These scenarios, fixtures,
metrics, limits, and acceptance criteria are required now so the architecture
can be tested later without inventing a target under pressure. No production
load testing is permitted by this document.

## Common test contract

- **Environment:** isolated synthetic deployment, synthetic endpoint or mock
  adapter, no production DNS/credentials, disposable tenant and content store.
- **Target:** 1,000 accepted messages/minute (16.7/s) sustained for 30 minutes,
  plus the declared burst profile; large-message tests are separate from the
  small-message throughput test.
- **Evidence:** commit SHA, fixture/profile versions, generator seed, request
  and operation counts, queue graphs, latency histograms, error/retry counts,
  resource graphs, checksums, and cleanup result.
- **Pass rule:** thresholds below must be agreed by QA and architecture before
  execution; any threshold change creates a decision-log entry.

## Scenarios

| ID | Workload and fixture | Metrics | Initial acceptance criteria | State |
| --- | --- | --- | --- | --- |
| PERF-01 | 1,000/min for 30 min; 90% small synthetic messages, 9% medium, 1% large; 1–5 attachments | accepted rate, p50/p95/p99 API admission, queue age, worker throughput, error rate | ≥1,000/min accepted for full window; no lost/duplicated operations; p99 and error limits recorded before run | Defined, not run |
| PERF-02 | 5-minute burst at 3× target followed by 20-minute drain | queue depth/age, 429/202 mix, recovery time, oldest operation age | Backpressure is visible; no unbounded memory; drain reaches zero or documented steady state within agreed time | Defined, not run |
| PERF-03 | Large messages at profile maximum and just over maximum; streamed/resumable attachments | upload memory, checksum CPU/time, transfer latency, resume bytes, reject code | Memory stays within worker budget; resume does not duplicate content; over-limit rejection is deterministic | Defined, not run |
| PERF-04 | Same idempotency key replayed concurrently and after timeout/crash | operation count, external-attempt count, duplicate side effects, conflict responses | One logical operation; same-body replay returns original; different-body replay is `409` | Defined, not run |
| PERF-05 | Kill/restart workers at pre-submit, post-submit, and post-receipt points | recovery time, lease expiry, event order, reconciliation count | No missing event; no unbounded retry; terminal evidence is explainable | Defined, not run |
| PERF-06 | Delay/fail object store and upstream with 429/5xx/timeouts | queue age, retry schedule, dead-letter count, backoff, alert latency | Retry budget and backoff are bounded; poison work is isolated; alerts include profile and operation | Defined, not run |
| PERF-07 | Scale workers 1→N→1 with per-tenant partitions | throughput/worker, rebalance time, lock contention, ordering | Throughput scales without cross-tenant leakage or duplicate side effects; degradation is measurable | Defined, not run |
| PERF-08 | Observability overhead at target load with redaction enabled | CPU/storage overhead, dropped telemetry, log cardinality | Required metrics remain available; no content/secret leakage; overhead limit is agreed before run | Defined, not run |

## Stop conditions

Stop immediately on any real endpoint resolution, real credential use, content
leak, cross-tenant result, duplicate external side effect, unbounded queue or
memory growth, or inability to account for a message in the evidence manifest.
