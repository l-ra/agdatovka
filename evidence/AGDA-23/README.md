# AGDA-23 — synthetic content ingress and attachment integrity

This is offline, synthetic evidence only. It is not proof of production object
storage, provider delivery, legal receipt semantics, or performance.

## Acceptance map

| Requirement | Source and test evidence | Result |
| --- | --- | --- |
| Stream bytes through a content-store seam | `ag_datovka/pipeline.py::ContentStore`; `tests/test_pipeline.py::test_streaming_manifest_checksums_without_joining_chunks` | Pass |
| Interrupted upload does not publish partial or duplicate content | `ContentStore.put` atomic temporary file handling; `test_interrupted_upload_is_not_published_and_resume_has_one_object` | Pass |
| Server digest and byte length are authoritative | `ag_datovka/app.py::_attachment_input`; `test_wsgi_octet_stream_ingress_and_malformed_transport_lengths` | Pass |
| Missing/non-integer/non-finite/negative/oversized lengths | `ag_datovka/app.py::_declared_length`; `test_declared_length_problem_semantics_are_stable` | Pass: 400/413 stable Problem JSON |
| Metadata-only uploads cannot claim verification | `tests/test_qa_conformance.py::test_attachment_metadata_is_rejected_and_declared_values_are_verified` | Pass: 415 |

## Reproduction

```text
python3 -m unittest tests.test_pipeline tests.test_qa_conformance
python3 -m unittest discover -s tests -v
```

The fixture at `fixtures/content/attachment-boundaries.json` is deterministic
and synthetic. The WSGI path is exercised with an in-memory byte stream; no
external object store or network endpoint is contacted.
