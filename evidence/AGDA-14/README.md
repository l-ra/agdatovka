# AGDA-14 independent security re-review evidence

The durable review is [the AGDA-14 security report](../../reporting/2026-10-30-agda14-security-review.md).

Reviewed remediation: `72d8d58f801a9820873982d9cc382796aa193009`.

Verification command:

```text
python3 -m unittest discover -s tests -v
```

Result: 29 tests passed in the synthetic environment. The two prior High
findings are accepted as remediated. The release verdict remains fail outside
synthetic/test scope because concurrent idempotency, malformed attachment
handling, and byte-bound content integrity remain unresolved; performance and
compatibility scenarios are explicitly deferred.
