# AGDA-26 P3-06 evidence

Synthetic/test-only evidence for retention, legal hold, export, restore, and
evidence rebuild. It is not production proof or a legal-compliance claim.

## Evidence

- Runtime: `ag_datovka/app.py`
- Policy/clock fixture: `fixtures/retention/policy.json`, `qa/retention.py`
- Legal/source traceability: `docs/requirements/AGDA-26-LEGAL-TRACEABILITY.md`
- Acceptance tests: `tests/test_management_api.py` and `tests/test_qa_conformance.py`
- Operator procedure: `docs/operations/RELEASE-RESTORE-RUNBOOK.md`

The restore report verifies the export digest, policy version, audit hash links,
message-event hash links, attachment checksums, tenant authorization scope,
trust-profile digests, pending-operation metadata, and that no send replay is
performed. Restore namespaces reject the production prefix and are intended for
disposable synthetic data only.

## Verification

`python3 -m unittest discover -s tests -v` — local repository regression evidence
for the synthetic slice. This is not production or legal-compliance proof.
