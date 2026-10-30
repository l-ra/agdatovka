# REQ-013 evidence

## Recorded result

On 2026-10-30 UTC, the offline compatibility harness passed with:

```text
profile:offline-fixture mode:offline parse receipt search export
```

The profile checks also passed for `ag-synthetic` and `isds-public-test`; they
remain `.invalid` placeholders and therefore do not perform network I/O.

Upstream provenance is pinned in `UPSTREAM.md` at commit
`67f1f23056e6f96e4a93632c11418a8ce8ca0b2f`. The local change is recorded in
`patches/0001-endpoint-profile-layer.patch` and the attribution boundary is in
`NOTICE`.

## Reproduction

```sh
fork/scripts/check.sh
```

Expected final line:

```text
fork checks: pass
```

This evidence demonstrates profile selection, production-host and inline
secret rejection, and offline fixture parsing. It does not claim a live
public-test run; that requires a separately approved synthetic account and
test endpoint. No production account, secret, trust bypass, or former
AGDatovka artifact is used.
