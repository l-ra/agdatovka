# AGDA-21 Phase 2 evidence reconciliation and contract freeze

## Disposition

Phase 2 is frozen as a synthetic/test-only contract. The evidence is
reconciled below; it does not authorize production deployment, external ISDS
interoperability, performance claims, or compliance claims.

## Exact provenance

| Item | Exact value |
| --- | --- |
| Source checkout branch | `agent/agda-1-foundation` |
| Source branch tip reviewed | `dce9120b634397d4811c15d6ba033674e5dc9c63` |
| Integrated local `main` reviewed | `9714cbf50ce08d075afce9005ef8b06c23e9ebdd` |
| Historical AGDA-16 integration evidence | `ad308dc` → `0595195` → `9714cbf` on local `main` |
| Read-only source mirror ref observed | `origin/agent/agda-1-foundation` at `e67b118d35379a082b536a7b4516c1a0b5aa523a` |
| Read-only foundation mirror ref observed | `origin/mirror/agda-16-foundation-dce9120` at `dce9120b634397d4811c15d6ba033674e5dc9c63` |
| Read-only integrated mirror ref observed | `origin/mirror/agda-16-integrated-9714cbf` at `9714cbf50ce08d075afce9005ef8b06c23e9ebdd` |

The historical failed mirror attempt is preserved in
`main:evidence/AGDA-16/mirror-verification.md` and its provenance commits. It
records that no push, force-push, merge, issue, or pull request was attempted.
The observed GitHub source ref is not an ancestor of the local source tip, so
the provider boundary remains divergent; these read-only refs are not proof
that GitHub contains the complete integrated tree.

## Reconciled evidence

### Baseline and 33-test report

The current synthetic baseline was verified with:

```text
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Result: **33 tests passed**, `OK` (2026-11-01 UTC clean export of the frozen
commit). This supersedes the historical AGDA-14 wording “29 tests passed” for
the current checkout; it does not change AGDA-14's adverse verdict.

### AGDA-14 adverse verdict

AGDA-14 remains **PASS for the two AGDA-12 High-finding remediations; FAIL
for release beyond the synthetic/local fixture**. Residual release blockers
F-003 concurrent idempotency, F-004 malformed attachment metadata, F-005
caller-supplied unverifiable attachment digests, and F-006 unexecuted
performance/compatibility evidence remain open. The 33-test result is local
regression evidence only and is not a security or production approval.

### AGDA-13 deferred performance status

AGDA-13 records executable readiness only. These validation commands remain
reproducible:

```text
python -m qa.performance_readiness --validate
python -m unittest tests.test_qa_conformance tests.test_performance_readiness
```

They validate manifests and safety gates; they do not generate load or prove
throughput, latency, capacity, recovery, or SLO attainment. Performance stays
**DEFERRED** pending QA and architecture approval and an approved isolated
synthetic run with commit, profile, seed, counts, latency, queue/resource,
checksum, and cleanup evidence.

### Reporting limitations

All claims are bounded to checked-in code, deterministic fixtures, and the
isolated synthetic/test profile. No production endpoint, credential, private
key, real message content, external ISDS request, deployment, legal opinion,
or compliance certification was used or established. Offline fixtures and a
readiness manifest are evidence of contract shape and safety checks only, not
production proof.

## Frozen synthetic contract

- Profile: `synthetic-ag-v1-2026-10-30`.
- Deterministic seed: `20261030`.
- Production DNS, credentials, private keys, and real message content are
  forbidden.
- The local API, pipeline, adapter, trust boundary, lifecycle fixtures,
  reporting checks, and validation-only performance harness are in scope.
- Performance execution, external compatibility, and deployment behavior are
  out of scope until their stated approval and evidence gates pass.
- Any future measured or interoperability result must carry an exact commit,
  fixture/profile identity, UTC command record, checksums, and redaction
  review; a readiness manifest or offline fixture must not be relabeled as
  production proof.

## Redaction review

The reviewed evidence contains no credentials, private keys, real message
content, personal data, or unpublished vulnerability details. Hostnames and
secrets appearing in negative-test fixtures are test inputs or documentation,
not runtime endpoints or credentials. The evidence intentionally retains
finding identifiers and limitations needed for review without reproducing
sensitive payloads.
