# Deferred performance scenarios

Performance execution is intentionally deferred. The scenarios are required
artifacts so the architecture remains testable:

- sustained 1,000 messages/minute with a defined message-size distribution;
- burst traffic and queue backpressure;
- large message and attachment streaming, checksum validation, retry, and
  resumable transfer;
- duplicate delivery requests and idempotency under retry;
- worker restart, storage delay, partial failure, and recovery;
- horizontal worker scaling and observability of latency, queue depth, error
  rate, and resource use.

Each future run will declare fixtures, environment, load profile, metrics,
thresholds, expected evidence, and cleanup. No production load testing is
permitted by this document.
