# AGDA-22 / P3-02 evidence

## Scope

This evidence covers synthetic/offline management API idempotency and
operation-state hardening. It does not use a production database, credentials,
real endpoints, or real messages, and it is not production proof.

## Implemented boundary

- `idempotency_keys` is unique on `(tenant_id, actor, key)`.
- A mutating request durably records a `claimed` row before routing, including
  request digest, claim timestamp, and attempt number.
- Completion stores the response and transitions the row to `completed`.
- Same-body replay returns the stored response; a different body returns
  `409 idempotency_conflict`.
- A crash before routing leaves a recoverable claim; the next same-body request
  increments attempts and completes it without a raw uniqueness error.
- The local request lock makes the single-process SQLite fixture deterministic;
  the constraint/error path also handles a cross-process uniqueness race.
- Durable outbox/queue processing records leases, attempts, exponential
  backoff, retry/dead-letter state, bounded in-flight work, lifecycle events,
  and immutable synthetic receipt evidence.

## Verification

Command:

```text
python3 -m unittest discover -s tests -v
```

Result: 38 tests passed in the synthetic environment, including:

- 100 concurrent same-body requests producing one box and 99 replays;
- different-body reuse returning `409 idempotency_conflict`;
- a deterministic route crash leaving `claimed`, attempt `1`, and no response,
  followed by recovery to `completed`, attempt `2`, with one box;
- outbox duplicate suppression, lease expiry, backoff, dead-letter, and
  backpressure tests.

## Source and review handoff

The implementation is in `ag_datovka/app.py` and `ag_datovka/pipeline.py`;
focused tests are in `tests/test_management_api.py` and
`tests/test_pipeline.py`. Reviewers should record findings on AGDA-22; this
fixture and readiness evidence must not be represented as production proof.
