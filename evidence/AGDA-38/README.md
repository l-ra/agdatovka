# AGDA-38 / AGDA-33 P4-05 synthetic send/receive vertical slice

This is dependency-free local proof of the synthetic domain path. It uses only
SQLite, synthetic boxes, the durable outbox/lease queue, and the versioned
`ag-isds-adapter-v1` fixture boundary. Real ISDS endpoints and credentials are
out of scope.

## Reproduction

```sh
python3 -m unittest tests.test_vertical_slice -v
```

Scenario declaration: [`fixtures/scenarios/synthetic-send-receive.json`](../../fixtures/scenarios/synthetic-send-receive.json).

The test covers sender and recipient boxes, a checksum-verified attachment,
transactional outbox dispatch, worker lease/idempotency evidence, receipt
validation and persistence before `delivered`, recipient inbox projection,
immutable receipt/audit export, legal hold/tombstone/isolated restore, and
recovery behavior. Injected receipt failure proves no receipt or `delivered`
projection is emitted without adapter evidence.

This is synthetic readiness evidence, not provider certification, legal advice,
or a performance result. Production queue, adapter transport, trust material,
and operational retention schedules remain deployment work.
