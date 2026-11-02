# AGDA-25 — P3-05 lifecycle receipt validation

Date: 2026-11-01 UTC  
Scope: offline `ag-synthetic` adapter and local synthetic management API only.

This evidence is not production interoperability proof, a legal delivery claim,
or approval of current ISDS rules/WSDL. The current-rules/WSDL approval remains
open in `docs/requirements/LEGAL-REGISTER.md` and the source register.

## Contract delivered

- `IsdsCompatibilityAdapter` preserves raw receipt bytes as a digest and
  base64 evidence value, emits validator/signature/chain/error metadata, and
  rejects invalid signature, chain, and declared-error cases closed.
- `GET /api/v1/messages/{messageId}/receipts/{receiptId}` retains the existing
  v1 fields and additively returns raw evidence, validation metadata, and
  `eventId`/`auditEventId` links. Stored evidence is digest-checked before it is
  returned; failure is `409 receipt_integrity_failure`.
- The synthetic worker links the receipt to the operation, delivered lifecycle
  event, and `receipt.validated` audit record. Export manifests embed the same
  immutable receipt record.

## Fixtures and tests

| Area | Fixture/test | Result |
| --- | --- | --- |
| EV mapping | `fixtures/isds/lifecycle.json`, `tests/test_isds_adapter.py::IsdsAdapterTest::test_lifecycle_all_required_codes_are_explicit` | PASS |
| Raw receipt and validation | `fixtures/isds/receipt.xml`, `fixtures/isds/receipt.zfo`, `tests/test_isds_adapter.py::IsdsAdapterTest::test_auth_receipts_and_round_trip_exports` | PASS |
| Fail-closed cases | `tests/test_isds_adapter.py::IsdsAdapterTest::test_receipt_signature_chain_and_error_cases_fail_closed` | PASS |
| End-to-end traceability | `tests/test_management_api.py::ManagementApiTest::test_worker_projects_delivery_receipt_and_immutable_evidence` | PASS |
| Full regression | `python3 -m unittest discover -s tests -p 'test_*.py'` | 46 passed |

The compatibility change is additive and requires no client migration: existing
v1 receipt fields remain present; new metadata fields can be ignored by older
clients.
