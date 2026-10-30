# AGDA-16 deterministic integration test report

Executed in a clean detached worktree at source tip
`dce9120b634397d4811c15d6ba033674e5dc9c63` before integration.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -p 'test_*.py' -v` | PASS — 33 tests |
| `python3 -m compileall -q ag_datovka qa tests` | PASS |
| `git diff --check` | PASS |
| `python3 -m qa.performance_readiness --validate` | PASS — validation only; no load run |
| `bash fork/scripts/check.sh` | PASS — offline fixture and two network profiles remained operator-action-required |

The checks used only repository fixtures and synthetic profiles. No production
host, credential, private key, real message, network request, or deployment was
used. The adverse AGDA-14 verdict remains authoritative for any scope beyond
this isolated synthetic/test gate.
