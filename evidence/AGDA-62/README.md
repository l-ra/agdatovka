# AGDA-62 ISDS SOAP/auth conformance evidence

## Scope and provenance

This report is an independent, deterministic exercise of the local public
compatibility boundary after AGDA-60 and AGDA-61. It uses only the pinned
fixtures under `fixtures/isds/` and `fixtures/security/`; endpoints, boxes,
certificates, receipts, message IDs, and payloads are synthetic. No live ISDS
endpoint, account, credential, private key, certificate, or personal data was
accessed.

The source profile is `isds-reference-2026-06-26`. The WSDL/XSD digests and
synthetic endpoint declarations are pinned in
`fixtures/isds/soap-manifest.json`. This is compatibility evidence for the
implemented fixture boundary, not a claim of official or live ISDS conformance.

## Exact reproduction

From the repository root:

```sh
python3 -m unittest tests.test_agda62_conformance -v
python3 -m unittest tests.test_soap_gateway tests.test_isds_adapter tests.test_security_boundary tests.test_pipeline -v
python3 -m unittest discover -s tests -t . -q
```

Observed on 2026-11-05: the full repository suite ran 95 tests and passed.
The synthetic certificate and application-auth fixtures now derive their
validity windows from an explicit test clock; the fork workflow shares one
run clock between fixture creation and validation. Production validators still
use wall-clock time, and expiry/replay remains covered by a prior-day negative
fixture.

## Traceability and observed results

| Area | Evidence | Result |
|---|---|---|
| WSDL operation surface | `test_pinned_wsdl_and_xsd_have_matching_operation_and_order_contract` | Eight WSDL operations match the gateway action map; CreateMessage order is messageId, subject, recipientBoxId, attachments; XSD allows 0–50 attachments. PASS |
| SOAP envelope/faults | `test_fault_matrix_preserves_safe_correlation_and_raw_provenance`, `tests/test_soap_gateway.py` | SOAP 1.1 namespace, POST-only method, endpoint, SOAPAction, sequence, attachment namespace/base64, correlation, and structured faults are checked. PASS |
| Lifecycle EV0–EV13 | `test_ev0_to_ev13_matrix_preserves_supported_codes_and_rejects_unmapped_codes` | EV0, EV2, EV3, EV5, EV6, EV8, EV11 map explicitly. EV1/EV4 legacy and EV7/EV9/EV10 unknown cases are rejected with `unknown_event_code`; EV12/EV13 are also rejected. No silent normalization. PASS |
| Auth/trust failures | `test_trust_negative_matrix_is_explicit`, `tests/test_security_boundary.py` | Expiry, hostname, key usage, revocation, chain/CA, identity binding, nonce expiry/replay, endpoint, and secret-handle failures remain fail-closed with stable synthetic codes. PASS |
| Raw receipt provenance | `test_receipt_raw_bytes_are_digestable_and_round_trip_exactly`, `tests/test_isds_adapter.py` | Raw byte length, SHA-256 digest, and base64 evidence decode to the exact fixture bytes; XML/ZFO parsing remains distinct. PASS |
| VoDZ boundaries | `test_vodz_inclusive_boundaries_and_fail_closed_overages` | 20 MiB and 100 MiB/50 attachments accepted at metadata boundary; 100 MiB + 1 byte, 51 attachments, and wrong `ws2` endpoint rejected. PASS |
| Streaming/retry/idempotency | `test_retry_key_and_receipt_evidence_survive_reinstantiation`, `tests/test_pipeline.py`, `tests/test_qa_conformance.py` | Chunked store, interruption cleanup/resume, retry backoff, dead-letter, durable side-effect key, replay-safe outbox, and evidence persistence are covered. PASS |
| Management/REST regression | `tests/test_management_api.py`, `tests/test_qa_conformance.py`, full suite | Existing `/api/v1` behavior remains green; no SOAP route is used as a management-auth bypass. PASS |

## Performance readiness (execution deferred)

No load or capacity measurement was executed. The runnable future scenarios are
already defined in `qa/performance-scenarios.json` and validated by
`tests/test_performance_readiness.py`, with the 1,000 accepted messages/minute
target, large/resumable content, idempotency replay, worker recovery, upstream
fault, resource, queue, and cleanup scenarios. Numeric hypotheses and stop
conditions are in `docs/testing/PERFORMANCE-THRESHOLDS.json` and
`docs/testing/PERFORMANCE-SCENARIOS.md`; the decision log records that execution
requires a separately approved synthetic environment.

## Limitations and adverse findings

- The WSDL/XSD and all protocol semantics are synthetic, versioned fixtures;
  official upstream schema equivalence is not established.
- The SOAP gateway validates wire shape but does not perform a live TLS
  handshake, certificate exchange, XML signature verification, or provider
  delivery.
- VoDZ size/attachment checks exercise adapter metadata and the bounded local
  boundary; they do not constitute a 100 MiB network transfer benchmark.
- EV1/EV4 are intentionally treated as legacy/unknown by this adapter profile,
  and EV7/EV9/EV10 are rejected. A deployment requiring those provider codes
  needs an explicit versioned mapping decision; accepting them implicitly would
  be a compatibility defect.
- Performance SLOs remain hypotheses, not measured results.
