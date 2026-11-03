# AGDA-44 — deployment attempt evidence

Run date: 2026-11-03  
Candidate source: `3660a354d59f6801c883df8592717481e6b6e264`

## Disposition

**Blocked before deployment.** The checked-out repository contains the
prepared Dockerfile, Compose stack, and reverse-proxy configuration, but the
computer running this agent does not expose a container runtime or a Docker
socket. No container, image, database, queue, object store, or public service
was started, and no deployment claim is made.

## Checks performed

- `docker --version`: command not found.
- `docker compose version`: command not found.
- `podman`, `nerdctl`, `docker-compose`, and `buildah`: unavailable.
- `/var/run/docker.sock`, `/run/docker.sock`, and
  `/run/containerd/containerd.sock`: unavailable.
- Paperclip execution workspace runtime services: none configured.
- `http://api.167-235-133-45.sslip.io/` (and the tested `management`,
  `user`, `web`, and `admin` variants): HTTP 308 redirect to HTTPS.
- `https://api.167-235-133-45.sslip.io/`: TLS handshake ends with
  `tlsv1 alert internal error`; application health cannot be verified.

## Repository verification

- `python3 -m unittest discover -s tests -p 'test*.py' -q`: 69 tests passed.
- `python3 -m qa.performance_readiness --validate`: manifest valid; load was
  not executed.
- `python3 -m compileall -q ag_datovka qa fork/scripts`: passed.
- `python3 fork/scripts/local_workflow.py`: synthetic workflow passed with
  redacted evidence.

## Required unblock action

An operator with access to the intended deployment host must provide a
working Docker/Compose runtime (or bind this task to the host that has it),
then configure the TLS terminator for the requested `*.167-235-133-45.sslip.io`
service names and run the release gate from
`docs/operations/RELEASE-RESTORE-RUNBOOK.md`. The deployment must record the
image digests, migration checksum, Compose health output, and final HTTPS
health checks before this task can be closed.
