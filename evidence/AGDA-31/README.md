# AGDA-31 — independent security re-review evidence

The committed review report is [`reporting/2026-11-01-agda31-independent-review.md`](../../reporting/2026-11-01-agda31-independent-review.md).

Reviewed commit: `140584e0da6fd14170488ab9809f622cc9994544`.

Reproduction result: `python3 -m unittest discover -s tests -v` — 58 passed;
compile, readiness validation, fork checks, and the in-process synthetic
workflow also passed. The review records two open high-severity findings:
same-tenant sender-identity impersonation (F-007) and unsigned OIDC-shaped
bearer acceptance (F-008). They block any release outside the isolated
synthetic fixture. This evidence is not a production security certification.
