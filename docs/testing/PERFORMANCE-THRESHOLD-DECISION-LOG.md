# Performance threshold decision log

## P3-10 / AGDA-30 — 2026-11-01

**Decision status:** QA proposal recorded; execution approval **not granted**.

The values below are numeric pre-run thresholds for review by QA and
Architecture. They are hypotheses for the declared synthetic resource profile,
not measurements and not production SLOs. A PERF run remains prohibited until
the approval and isolated synthetic/loopback environment are recorded.

| Measure | Proposed threshold | Scope and interpretation |
| --- | ---: | --- |
| Accepted rate | ≥ 1,000 messages/minute | PERF-01 sustained window; accepted means validated API acceptance |
| Admission latency | p99 ≤ 750 ms | PERF-01, successful admissions only |
| Error rate | ≤ 1.0% | PERF-01, unexpected 5xx/transport errors; expected backpressure responses are counted separately |
| Queue drain | ≤ 15 minutes | PERF-02 after the declared 5-minute 3× burst |
| Worker memory | ≤ 512 MiB | PERF-02/03/10 per worker, matching the manifest budget |
| Retry budget | ≤ 5 attempts per operation | PERF-05/06, including the initial attempt; poison work is not retried |
| Telemetry overhead | ≤ 15% CPU and 0 dropped required events | PERF-08 compared with the same synthetic workload with telemetry disabled; no content/secret findings |
| Lost operations | 0 | All PERF scenarios |
| Duplicate operations/side effects | 0 | All PERF scenarios |

### Rationale and open approval

The proposals are bounded by the checked-in resource assumptions (two API
instances, two workers, four queue partitions, ten fixed tenants, 512 MiB
worker/generator budgets, and 10,000 maximum queue depth). They are intended
to make a future run falsifiable and reproducible. Architecture must either
approve these values or record replacements before execution; any replacement
must update this decision log and the performance manifest in the same change.

### Safety gate

Abort immediately on production DNS, credentials, real content, cross-tenant
results, duplicate external side effects, unbounded queue/memory growth,
telemetry redaction failure, or an unaccounted operation. No such load run was
attempted for AGDA-30.
