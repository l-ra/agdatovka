# ADR-012 — Deployable runtime and persistence boundary

- **Status:** accepted for the Phase 4 foundation
- **Decision:** Deploy API and worker as separate non-root containers. Use a
  relational database for metadata and migrations, an S3-compatible persistent
  object store for message content, and a durable Redis/AMQP-compatible queue
  for outbox dispatch and worker leases. The web role is a reverse proxy; it
  does not own application state.
- **Fixture exception:** `ag_datovka.app.Database` and `ContentStore` remain
  dependency-free SQLite/filesystem fixtures for unit and contract tests.
  `AG_ENV=deploy|production` rejects SQLite, file object storage, and memory
  queues through `RuntimeConfig`.
- **Security:** credentials are injected by the deployment secret manager.
  `.env.example`, Compose, and image metadata contain no production secrets or
  hostnames. The image runs as UID/GID 10001 and has a read-only root.
- **Health:** `/health/live` checks process liveness without authentication;
  `/health/ready` checks the metadata boundary and is suitable for traffic
  gating. Neither endpoint exposes credentials or message content.
- **Trade-off:** provider clients and the migration runner are explicit
  adapters, not silently added dependencies to the synthetic fixture. This
  keeps tests deterministic while making the production wiring reviewable.

## Evidence

`Dockerfile`, `.dockerignore`, `docker-compose.yml`, `migrations/001_runtime_boundary.sql`,
`ag_datovka/config.py`, and `tests/test_runtime_boundary.py` define the
reproducible boundary. The backup/restore procedure is in
`docs/operations/RELEASE-RESTORE-RUNBOOK.md`; performance execution remains
deferred per the existing performance decision log.

