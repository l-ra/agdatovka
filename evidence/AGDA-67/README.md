# AGDA-67 synthetic SOAP attachment-limit evidence

## Contract

The pinned synthetic SOAP/XSD contract accepts `CreateMessage` with 0–50
attachments. The SOAP gateway counts attachment children while parsing the
wire request. A 51st child returns the deterministic `Client.AttachmentLimit`
SOAP 1.1 fault before adapter normalization or attachment decoding. The fault
includes the request and correlation IDs and is byte-for-byte stable for the
same request and headers.

The decoded attachment aggregate is also bounded at an inclusive 100 MiB,
matching the synthetic VoDZ `sizeBytes` limit. This is an adapter boundary for
decoded bytes; the SOAP request’s existing 100 MiB raw XML limit remains a
separate wire-size guard.

## Reproduction and result

```sh
python3 -m unittest tests.test_soap_gateway tests.test_agda62_conformance -v
```

Observed result: exact-50 SOAP input passed; 51-attachment input returned
`Client.AttachmentLimit` twice with identical fault bytes, left the normalized
result empty, and did not call the adapter a second time. The decoded-byte
tests accepted exactly 100 MiB and rejected 100 MiB plus one byte.

All inputs are generated in-memory synthetic fixtures. No live endpoint,
production credential, private user data, or real certificate material was
used.
