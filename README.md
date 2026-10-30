# AG Datovka 2

Independent reimplementation of public databox interfaces.

This project starts from a clean repository. It is not a continuation of the
previous AGDatovka implementation and it does not implement migration of
existing data. Migration is a separate project. The compatibility target is
the public interface and workflow behavior needed after a future migration.

## Development rules

- Paperclip manages task state, dependencies, reviews, approvals, and agents.
- Git stores every durable artifact: source, tests, fixtures, requirements,
  evidence, decisions, runbooks, and reports.
- Every task uses an isolated worktree and branch.
- Integration happens locally through the Paperclip Release Integration agent;
  GitHub is a mirror and human inspection surface.
- GitHub Issues and Pull Requests are not part of project control.
- Performance execution is deferred, but architecture and reproducible
  scenarios target 1,000 messages per minute and large messages.

## Initial scope

The first implementation slices cover a management interface for creating a
databox and sending messages, stable public contracts, modern versioned APIs
and authentication, trust/certificate configuration, audit evidence,
CZ.NIC Datovka compatibility, and a separately documented Datovka desktop
fork.

See `docs/` for the source/legal registers, requirements traceability,
compatibility matrix, target architecture and decisions, management API,
security/trust model, data-flow/retention model, test strategy, CZ.NIC and
Datovka fork plans, deferred performance scenarios, and release/restore
runbook. Human-readable progress is published from the `reporting` branch via
GitHub Pages.
