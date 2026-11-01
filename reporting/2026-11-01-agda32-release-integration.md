# AGDA-32 release integration milestone — 2026-11-01

## Disposition

This is a local release-integration record for the isolated synthetic/test
milestone. It is not a production release, deployment authorization, legal or
compliance opinion, external ISDS delivery result, or public-test approval.

The integrated candidate is **conditionally usable for synthetic/test evidence
only**. The independent security review remains adverse outside that boundary:
F-007 same-tenant sender impersonation and F-008 unsigned OIDC-shaped bearer
acceptance remain open release blockers. Performance execution, external
interoperability, HA/process recovery, migration, and production authorization
remain unproven.

## Exact provenance

| Item | Value |
| --- | --- |
| Source branch | `agent/agda-1-foundation` |
| Source candidate commit | `00a8f3b5eaccc325c62ac0073495efb52e82ab47` |
| Integration base (`main`) | `9714cbf50ce08d075afce9005ef8b06c23e9ebdd` |
| Local no-fast-forward merge commit | `0a24b8bda6140ffe4e716c063cd905e3fae9b055` |
| AGDA-31 reviewed candidate | `140584e0da6fd14170488ab9809f622cc9994544` |
| AGDA-30 evidence commit | `140584e0da6fd14170488ab9809f622cc9994544` |
| AGDA-29 implementation/evidence commit | `9998654` (source history) |
| Synthetic fixture profile | `synthetic-ag-v1-2026-10-30`, seed `20261030` |

The merge was performed locally with `git merge --no-ff` in an isolated
detached integration worktree. The merged tree retains five main-only release
evidence files and adds the complete source candidate; there are no source
deletions. `git diff --check` passed.

## Verification

All commands ran from the exact source candidate before integration and were
repeated/inspected against the merged tree as applicable:

| Check | Result |
| --- | --- |
| `python3 -m py_compile ag_datovka/*.py qa/*.py fork/scripts/*.py` | PASS |
| `python3 -m unittest discover -s tests -p 'test_*.py' -v` | PASS — 58 tests |
| `python3 -m qa.performance_readiness --validate` | PASS — validation only; no load |
| `fork/scripts/check.sh` | PASS |
| `python3 fork/scripts/local_workflow.py --manifest /tmp/agda32-local-workflow.json` | PASS — in-process synthetic fixture |
| Secret/production-host fixture scans | PASS — covered by conformance/fork checks |
| Restore/tamper and blind-send replay protections | PASS — synthetic fixture tests |

The workflow reported `http://127.0.0.1:0/api/v1` in-process isolation and
export manifest digest
`sha256:c709a40ba6fd9b24855cb02bb55a4bbbaff9300b686f04a3e43baa855c8f7ef5`.
This is local fixture evidence only.

## Mirror plan and limitations

The source candidate and integrated result are mirrored only to named,
non-protected refs:

- `refs/heads/mirror/agda-32-source-00a8f3b`
- `refs/heads/mirror/agda-32-integrated-0a24b8b`

No protected ref, GitHub Issue, pull request, deployment, force-push, real
credential, production endpoint, or real message content is used. The mirror
result and exact remote object IDs are recorded on AGDA-32 after push
verification; a failed push must keep this gate closed.

