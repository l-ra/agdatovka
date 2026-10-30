# AGDA-15 compatibility and conformance release gate

## Decision

**PASS for the offline synthetic compatibility/conformance scope.** The gate
was executed on 2026-10-30 UTC at commit `72d8d58f801a9820873982d9cc382796aa193009`.
No production endpoint, account, credential, private key, trust bypass, or
real message content was used.

The performance execution gate remains **DEFERRED**. It requires the
documented QA and architecture approval before any load run; this release gate
does not claim the 1,000 accepted messages/minute target.

## Reproduction

Run from the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m compileall -q ag_datovka qa tests
git diff --check
bash fork/scripts/check.sh
```

Observed results on the recorded run:

- `29` unit/conformance tests passed.
- Python bytecode compilation passed.
- `git diff --check` passed.
- `fork/scripts/check.sh` passed for `offline-fixture`, `ag-synthetic`, and
  `isds-public-test`.
- Network profiles remained explicit-operator-action-required and `.invalid`;
  no network request was made.

## Covered gate assertions

| Area | Evidence | Result |
| --- | --- | --- |
| Public/modern API semantics | `tests/test_management_api.py`, `tests/test_qa_conformance.py` | PASS |
| Message, attachment, receipt, export, and audit evidence | `tests/test_isds_adapter.py`, `tests/test_management_api.py`, `fixtures/isds/*` | PASS |
| Lifecycle/event compatibility (`EV0`, `EV2`, `EV3`, `EV5`, `EV6`, `EV8`, `EV11`) | `fixtures/isds/lifecycle.json`, `tests/test_isds_adapter.py` | PASS |
| Large-message and attachment boundaries | `tests/test_qa_conformance.py`, `ag_datovka/isds_adapter.py` | PASS |
| Search/export determinism and idempotency | `tests/test_qa_conformance.py`, `tests/test_management_api.py` | PASS |
| Trust store, certificate, hostname, key usage, revocation, and secret handles | `fixtures/security/trust-vectors.json`, `tests/test_security_boundary.py` | PASS |
| Negative authorization and tenant isolation | `tests/test_management_api.py`, `evidence/AGDA-12/README.md` | PASS |
| Datovka fork profile selection and offline workflow | `fork/profiles/*.yaml`, `fork/scripts/check.sh`, `tests/test_fork_smoke.py` | PASS |
| Deterministic fixture/secret/production-host scanning | `qa/fixtures.json`, `qa/scans.py`, `tests/test_qa_conformance.py` | PASS |
| Performance target execution | `docs/testing/PERFORMANCE-SCENARIOS.md` | DEFERRED / approval required |

## Exact synthetic input set

The gate consumes these versioned inputs and tests:

```text
fixtures/api/v1/contract.json
fixtures/isds/{auth,envelope,errors,lifecycle,manifest,receipt.xml,receipt.zfo}
fixtures/pipeline/faults.json
fixtures/security/trust-vectors.json
fork/profiles/{ag-synthetic,isds-public-test,offline-fixture}.yaml
fork/fixtures/message.json
qa/{fixtures.json,fixtures.py,metrics.py,retention.py,scans.py}
tests/{test_fork_smoke,test_isds_adapter,test_management_api,test_pipeline,test_qa_conformance,test_security_boundary}.py
```

The ISDS fixture manifest pins profile `isds-reference-2026-06-26`, synthetic
box `synthetic-box-001`, and `.invalid` endpoints. The source and observed
protocol constraints are pinned in
`docs/compatibility/ISDS-SOURCE-MANIFEST.json`; the Datovka fork provenance is
pinned in `fork/UPSTREAM.md` and its local patch in
`fork/patches/0001-endpoint-profile-layer.patch`.

The shared checkout also contained an untracked `tests/__init__.py` before this
evidence file was added. It was preserved and not relied upon as a release
artifact change.

## Security and scope boundary

The profiles require operator-supplied trust-store, certificate, and
credential references for any future synthetic network run. Placeholders are
not credentials. `fork/scripts/check.sh` rejects production hosts and inline
secrets; the trust-vector tests reject expired, wrong-host, wrong-usage,
revoked, and unknown-CA certificates. Any public-test execution remains a
separately approved synthetic-account activity and is outside this offline
gate.

