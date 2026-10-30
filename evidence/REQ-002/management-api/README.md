# REQ-002 / REQ-006 / REQ-007 / REQ-009 management API evidence

Status: implemented in the standalone local foundation. This is synthetic
contract evidence, not a production deployment or a legal/compliance claim.

## Scope

- Source: `ag_datovka/app.py` and `ag_datovka/server.py`.
- Public schema: [`docs/management/openapi.v1.json`](../../../docs/management/openapi.v1.json).
- Deterministic fixture: [`fixtures/api/v1/contract.json`](../../../fixtures/api/v1/contract.json).
- Tests: [`tests/test_management_api.py`](../../../tests/test_management_api.py).
- Local setup uses a fresh SQLite database; it has no migration step and no
  dependency on the former AGDatovka implementation.

## Verified scenarios

The test suite verifies box/identity/policy metadata, metadata-only auth-method
registration, message metadata and lifecycle operations, export manifests,
RFC 9457-style problem responses, authorization denial, tenant isolation,
opaque bounded cursor pagination, idempotency replay/conflict behavior, and
hash-linked append-only audit records. Denied requests are recorded with actor,
tenant, request/correlation IDs, policy version, outcome, and reason.

Run from the repository root:

```text
python3 -m unittest discover -s tests -v
```

Verified result: `Ran 5 tests in 0.012s` followed by `OK`.
The final verified commit SHA and mirror status are recorded in the AGDA-3 task
handoff comment.

## Deliberate boundaries and limitations

- `Bearer dev:platform` and `Bearer dev:<boxId>:<identityId>` are test-only
  local tokens. A deployed service must replace them with scoped modern auth.
- Attachment requests accept a metadata/digest manifest in the direct fixture
  harness; the server boundary rejects unbounded direct JSON handling and the
  production content path remains a separate streaming/object-store slice.
- Operations are queued/cancellable metadata only. No ISDS SOAP or upstream
  delivery is implemented here.
- SQLite is for migration-free local development and deterministic tests, not a
  claim about production HA, throughput, retention, or legal sufficiency.
