# AGDA-7 QA evidence

This is the synthetic-only conformance boundary for REQ-004, REQ-005, REQ-010,
REQ-011, REQ-012, and REQ-014. Performance execution is intentionally deferred.

Reproduce with:

```text
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The run uses `qa/fixtures.json`, profile `synthetic-ag-v1-2026-10-30`, seed
`20261030`, and does not resolve an endpoint, use credentials, or create real
message content. Any future report must include commit, UTC timestamps, profile,
command, checksums, and redaction review.

| Requirement | Evidence |
| --- | --- |
| REQ-004 | EV0/EV2/EV3/EV5/EV6/EV8/EV11 lifecycle fixtures |
| REQ-005 | export manifest digest and immutable retrieval test |
| REQ-010 | explicit timeout/429/5xx/poison/crash fault plan |
| REQ-011 | `PERFORMANCE-THRESHOLDS.json`; no load run |
| REQ-012 | fixture manifest and secret/production-host scan |
| REQ-014 | weekend/holiday clock, 90/100-day profile, legal-hold tests |

Performance requires QA and architecture approval, an isolated synthetic
endpoint, and a disposable tenant/store. Stop conditions in the threshold
manifest invalidate a run and require a disposition.
