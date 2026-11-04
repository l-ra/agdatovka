# AGDA-63 Datovka fork workflow evidence

Status: pass for the local synthetic compatibility scope. This run used the
Datovka fork pin `67f1f23056e6f96e4a93632c11418a8ce8ca0b2f`, the repository
commit recorded in the generated manifest, and the `ag-synthetic` endpoint
profile. The harness is offline and uses no account, certificate, private key,
production host, or user data.

## Reproduction

```sh
fork/scripts/check.sh
python3 fork/scripts/local_workflow.py --manifest /tmp/agda-63-fork-manifest.json
python3 -m unittest tests.test_fork_workflow tests.test_fork_smoke tests.test_soap_gateway -v
```

The workflow covers login, list, send, receive, download, delivery receipt,
search, and export. SOAP probes exercise `Authenticate`, `GetListOfMessages`,
`CreateMessage`, `GetMessage`, and `GetDeliveryInfo`; REST checks retrieve the
message and attachment bytes, then validate the receipt, search result, and
export completion. The manifest is redacted and contains no message content or
secret material.

## Classification

- Compatible: SOAP 1.1 envelope, namespace, SOAPAction, correlation/request
  IDs, operation shapes, and the local message workflow.
- Intentional synthetic limitation: the gateway accepts and normalizes the
  pinned fixture surface; it does not claim live ISDS delivery. A Qt desktop
  build is also outside this dependency-free harness.
- Blocker: none for the approved synthetic scope.

The public-test profile remains a `.invalid` placeholder and was not contacted.
