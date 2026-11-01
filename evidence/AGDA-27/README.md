# AGDA-27 observability and abuse-resistance evidence

This is synthetic/offline evidence only. It is not production telemetry,
production authorization proof, or a readiness manifest.

## Controls

| Control | Source/test | Result |
| --- | --- | --- |
| Structured redacted records and request/correlation/operation IDs | `ag_datovka/observability.py`; `test_context_and_redaction_never_emit_sensitive_fields` | Sensitive keys, bearer values, payloads, and private-key markers are redacted; IDs are bounded and metadata-only |
| Queue/worker/retry/latency metrics and alerts | `DurablePipeline.metrics()`; `Telemetry.worker_result()`; `test_metrics_latency_worker_and_alerts` | Dead letters and global/tenant backpressure produce alert conditions; latency is numeric metadata |
| Trace sampling policy | `TraceSampler`; `test_sampling_keeps_faults_and_is_deterministic_for_success` | 5% deterministic success default; errors, denied events, and dead letters are always retained |
| Audit tamper detection/rebuild | `AuditLedger`; `test_audit_tamper_is_detected_and_rebuild_is_valid`; app audit-chain tests | Hash-chain mutation fails verification; offline rebuild produces a valid chain |
| Secret/production-host scans | `qa/scans.py`; `tests/test_qa_conformance.py` | Checked-in synthetic fixture scan is empty; negative secret/host probes are rejected |
| Negative authorization | `tests/test_observability_security.py::test_negative_authorization_cannot_cross_tenant_or_manage_global_policy` | Cross-tenant resource access and global policy mutation return stable denial responses |

## Reproduction

```text
python3 -m unittest tests.test_observability_security tests.test_qa_conformance -v
python3 -m unittest discover -s tests -v
```

The test output is reproducible from the exact commit containing this record.
No fixture contains message content, real personal data, credentials, tokens,
private keys, or production telemetry. Existing pipeline metrics remain the
source of queue/retry/dead-letter counters; this module provides the
content-safe emission and alert policy seam around them.
