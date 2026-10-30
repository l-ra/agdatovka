# REQ-003 / REQ-010 streaming pipeline evidence

Synthetic-only evidence for the durable content and message pipeline. No
production endpoint, credential, or data migration is used.

- Profile/fixtures: `synthetic-pipeline-v1`, `fixtures/pipeline/faults.json`
- Verification: `python3 -m unittest tests.test_pipeline tests.test_management_api`
- Covered: incremental checksum manifests, atomic object publication, outbox
  deduplication, durable queue dispatch, leases and restart recovery, bounded
  exponential retry, dead letters, and explicit in-flight backpressure.
- Deferred: performance execution; the queue default is sized for the stated
  1,000 messages/minute scenario without running a load test.
- Adapter boundary: `DurablePipeline.process_once` accepts an injected handler;
  the repository contains no upstream adapter or delivery claim.
