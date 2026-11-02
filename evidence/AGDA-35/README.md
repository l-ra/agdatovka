# AGDA-35 — deployable container runtime and persistence boundary

This slice establishes a clean-checkout deployment foundation after the
security contract. It does not claim a production deployment, external
delivery, or completed performance execution.

| Requirement | Evidence | Result |
|---|---|---|
| Clean non-root image | `Dockerfile`, `.dockerignore` | UID/GID 10001, read-only Compose root, no source secrets |
| Separate runtime roles | `docker-compose.yml`, `deploy/nginx.conf` | API, worker, web, Postgres, Redis, and persistent object-store roles are explicit |
| Relational persistence boundary | `migrations/001_runtime_boundary.sql`, `docs/architecture/ADR-012-DEPLOYMENT-BOUNDARY.md` | PostgreSQL is required for deploy/production; SQLite remains fixture-only |
| Deterministic configuration | `ag_datovka/config.py`, `.env.example` | Missing/ephemeral deploy endpoints fail closed; no credentials or production hostname is embedded |
| Health/readiness | `ag_datovka/app.py`, `tests/test_runtime_boundary.py` | Unauthenticated liveness and DB-backed readiness probes |
| Durable processing wiring | Compose queue volume, worker role, migration outbox | Redis AOF and transactional outbox boundary are declared; provider consumer remains an adapter |
| Operations evidence | `docs/operations/RELEASE-RESTORE-RUNBOOK.md` | Migration checksum, backup, isolated restore, and no blind replay are required |

## Verification

```text
python3 -m unittest tests.test_runtime_boundary tests.test_management_api tests.test_oidc_security
Ran 19 tests ... OK
```

No Docker build, external service startup, or performance test was run in this
synthetic checkout. The image and Compose file are intended for the approved
integration environment; credentials must be injected there.

