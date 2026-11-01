# AGDA-24 — durable worker reconciliation and backpressure

Candidate synthetic evidence for P3-04. This is a local fixture milestone;
it is not production delivery proof, an external ISDS receipt, or a load-test
result.

## Implementation map

| Requirement | Evidence |
| --- | --- |
| Operation/outbox atomicity | `ag_datovka/app.py` submit route uses `DurablePipeline.enqueue(..., commit=False)` and commits the operation, projection, audit, and outbox together. Route exceptions roll back the transaction. |
| Durable dispatch and leases | `ag_datovka/pipeline.py`; `tests/test_pipeline.py::StreamingPipelineTest::test_backpressure_and_lease_expiry_allow_recovery` |
| Stable attempts and adapter protection | `pipeline_side_effects`, `prepare_side_effect`, and `record_side_effect`; keys are `operationId:attempt:N`. |
| Retry/backoff/dead letters | `tests/test_pipeline.py::StreamingPipelineTest::test_retry_backoff_dead_letter_and_restart_recovery`; poison coverage in `test_poison_is_dead_lettered_without_retry`. |
| Tenant backpressure | `tenant_max_in_flight` and `test_tenant_backpressure_and_reconciliation_key_survive_restart`. |
| Crash checkpoints | `tests/test_management_api.py::ManagementApiTest::test_worker_reconciles_post_submit_and_post_receipt_crashes`. |
| Fault plan | `fixtures/pipeline/faults.json` covers 429, 5xx, timeout, poison, tenant admission, pre-submit, post-submit, and post-receipt restart cases. |

## Verification

```text
python3 -m unittest discover -s tests -v
Ran 45 tests ... OK
```

No performance test was run. The configured queue and tenant bounds are
backpressure controls, not evidence of the 1,000 messages/minute target.
Only `ag-synthetic-v1` adapter evidence can produce the local `delivered`
projection; this slice never calls an external service.
