# AGDA-60 synthetic ISDS SOAP/WSDL evidence

## Scope

Implemented the offline SOAP 1.1 wire boundary in
`ag_datovka/soap_gateway.py`. It accepts only the pinned synthetic operation
surface on `/isds/ws`, preserves SOAP namespaces, operation names, SOAPAction,
element order, request/correlation IDs, and base64 attachment validation, and
returns structured SOAP 1.1 faults. `/isds/ws2` is reserved for the large
message profile and rejects the standard matrix. `/api/v1` management and REST
behavior are unchanged.

## Pinned evidence

`fixtures/isds/soap-manifest.json` records source profile
`isds-reference-2026-06-26`, retrieval date `2026-10-30T00:00:00Z`, synthetic
endpoints, and SHA-256 digests for `soap-v20.wsdl` and `soap-v20.xsd`.
All names, endpoints, certificates, and payloads are synthetic; no live ISDS
endpoint, credentials, keys, certificates, personal data, or production
payloads were used.

## Verification

```sh
python3 -m unittest tests.test_soap_gateway -v
python3 -m unittest discover -s tests -q
```

Observed result: focused SOAP contract suite 5 tests passed; repository suite
83 tests passed.

## Failure and limitation report

- Namespace, sequence, missing/malformed content, malformed base64 attachment,
  SOAPAction, unsupported operation, method, and endpoint failures are mapped
  to stable SOAP faults with safe detail and correlation metadata.
- The normalized result is not substituted for raw XML or fault evidence;
  `SoapExchange` keeps those values separate.
- The gateway is a compatibility fixture, not a network client or production
  ISDS implementation. It does not perform certificate authentication,
  signature validation, live message retrieval, or live delivery.
- The WSDL/XSD are synthetic versioned evidence and should not be represented
  as official upstream schemas.
