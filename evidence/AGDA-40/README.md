# AGDA-40 — CI security and reproducible release evidence

Run date: 2026-11-02  
Candidate source before evidence commit: `94976f2234d7d96b09d3527be12acd46c39eeddd`

## Result

The dependency-free release matrix passes. A true Git-archive checkout was
also verified after the `local_workflow.py` provenance fix: 69 tests pass, the
synthetic send/receive workflow passes, deploy configuration rejects fixture
storage/auth/queue settings, and live/readiness health checks return `ok`.

Performance execution remains **deferred**; only the validation-only scenario
manifest was run. No production, provider, legal, HA, or performance claim is
made.

## Reproduction

Commands run from the repository root:

```text
python3 -m unittest discover -v                         # 69 passed
python3 -m qa.performance_readiness --validate           # manifest valid; no load
python3 -m unittest tests.test_qa_conformance tests.test_performance_readiness -v  # 16 passed
python3 -m unittest discover -s tests -p 'test*.py' -q  # 69 passed from clean archive
python3 fork/scripts/local_workflow.py                  # pass; redacted manifest
python3 -m compileall -q ag_datovka qa fork/scripts     # pass
```

The clean archive was created with `git archive HEAD`, then the candidate
workflow patch was applied and tested with `AG_COMMIT` set to the candidate
source SHA. Default `unittest discover` is not a valid clean-archive command
because `tests/__init__.py` is untracked in the workspace; explicit
`-s tests -p 'test*.py'` discovery is the reproducible command.

## Security and boundary evidence

- Fixture/secret/production-host negative and positive scans: pass through
  `tests.test_qa_conformance`, `tests.test_fork_smoke`, and
  `tests.test_performance_readiness`.
- Signed-token, revocation, tenant-binding, sender authorization, RBAC,
  redaction, attachment integrity, receipt integrity, idempotency, lease
  recovery, accessibility, and UI contract tests: included in the 69-test
  pass.
- Deploy config accepts PostgreSQL + S3 + Redis + deploy auth, and rejects
  SQLite, in-memory queue, and fixture auth: pass.
- Direct `/health/live` and `/health/ready` smoke: pass; both returned JSON
  status `ok`.
- Retention export/restore verification and tamper fail-closed behavior: pass
  in management and vertical-slice tests; `blindSendReplay` remains false.
- `Dockerfile`, Compose, migration, API contract, and release/restore runbook
  are present and included in the candidate source.

## Deferred / blocked execution

The runner has no `docker` executable (`docker --version` and `docker compose
version` both returned command-not-found). Therefore image build, Compose
startup, container migrations, container health, and deploy-profile backup /
restore could not be executed here. No Docker, SBOM, image digest, or
container-security result is claimed. The release integration environment must
rerun those gates and attach image/package digests plus migration checksums.

The available repository has no `syft`, `trivy`, `grype`, or `gitleaks`
binary. Repository-native fixture scans and security tests passed; external
SBOM and scanner evidence remains open.

## Release handoff

Use the final Git commit containing this report and the workflow provenance fix
as the exact evidence SHA. The release integration engineer must record the
merge SHA, image digest, migration checksum, SBOM digest, Compose logs, and
deploy-profile backup/restore report before release review.
