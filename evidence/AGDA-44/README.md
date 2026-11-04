# AGDA-44 — deployment attempt evidence

Run date: 2026-11-03  
Candidate source: `3660a354d59f6801c883df8592717481e6b6e264`
Verification checkout: `bffaa219f0b5cbd2e1fbedc9133e0dae0d54f1f4`
Public probe time: `2026-11-03T21:15Z`

## Disposition

**Public deployment verified.** The target HTTPS services are responding from
the requested `sslip.io` names. The agent workspace still does not expose a
Docker CLI or socket, so this run verifies the deployed result over HTTPS but
does not claim host-level Compose access or independently capture image and
migration metadata.

## Checks performed

- `docker --version` and `docker compose version`: command not found in the
  agent workspace; no host socket is exposed to this run.
- `http://api.167-235-133-45.sslip.io/`, `management`, and `user`: HTTP 308
  redirect to HTTPS.
- `https://api.167-235-133-45.sslip.io/health/live`: HTTP 200, JSON liveness
  status `ok`.
- `https://api.167-235-133-45.sslip.io/health/ready`: HTTP 200, JSON readiness
  status `ok`, database `ok`.
- `https://api.167-235-133-45.sslip.io/api/v1/boxes`: HTTP 401 with the
  expected `authentication_required` problem response when no token is sent.
- `https://management.167-235-133-45.sslip.io/`: HTTPS 200; AG Datovka
  synthetic management console content verified.
- `https://user.167-235-133-45.sslip.io/`: HTTPS 200; AG Datovka user interface
  content verified.
- `web` and `admin` service names: TLS alert `internal error`; these names are
  not counted as verified interfaces.

## Repository verification

- `python3 -m unittest discover -s tests -p 'test*.py' -q`: 69 tests passed.
- `python3 -m qa.performance_readiness --validate`: manifest valid; load was
  not executed.
- `python3 -m compileall -q ag_datovka qa fork/scripts`: passed.
- `python3 fork/scripts/local_workflow.py`: synthetic workflow passed with
  redacted evidence.

## Evidence limits

The public HTTPS checks establish that the API, management UI, and user UI are
currently reachable and healthy. Image digests, migration checksum, and raw
Compose health output remain host-level evidence that was not exposed to this
agent run; they must be captured by the deployment operator if required for a
release manifest. No production-data or production-credential claim is made.
