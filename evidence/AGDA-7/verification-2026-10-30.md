# AGDA-7 verification evidence

Verification was rerun against parent commit `75782b2` (which includes the
materialized `ag_datovka.security` module) on 2026-10-30 UTC.

## Reproduction

```text
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m compileall -q ag_datovka qa tests
```

Result: **27 tests passed**, bytecode compilation passed, and `git diff
--check` passed.

## Scope checks

- JSON parsing passed for 9 synthetic fixture/configuration manifests.
- Production-host and secret-like-value scan returned `[]` across the checked
  fixture/configuration manifests.
- Traceability covers REQ-004, REQ-005, REQ-010, REQ-011, REQ-012, and
  REQ-014 through `tests/test_qa_conformance.py` and the evidence matrix in
  `README.md`.
- Deferred performance gate remains `deferred` and requires
  `QA_AND_ARCHITECTURE_APPROVAL_REQUIRED` before execution.
- The future target remains 1,000 accepted messages/minute for 30 minutes;
  large-message profiles remain max-size, one-byte-over-max, and resumable-
  interrupted.

No production endpoint, credential, load run, or real message content was
used. The untracked `tests/__init__.py` present in the shared checkout was
preserved and is not part of this evidence change.
