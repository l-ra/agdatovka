# AGDA-10 release manifest

| Field | Value |
| --- | --- |
| Source commit | `75782b28324c82d60b2323b7115ce8312fe9a767` |
| Source branch | `agent/agda-1-foundation` |
| Integration merge commit | `e3ae3126a195000fbad396babebad469a0137fc0` (non-FF merge of source `75782b28324c82d60b2323b7115ce8312fe9a767`); final ancestry-reconciliation merge `c8793553d2033fd09d043d517006d2ed95f06f95` |
| API/schema version | `/api/v1`; OpenAPI document `docs/management/openapi.v1.json` |
| Fixture version | `fixtures/api/v1/contract.json` (repository commit version) |
| Adapter/WSDL checksums | Not applicable; no external adapter or WSDL is included |
| Image/package digests | Not applicable; no image or packaged release produced |
| Database migration identifier | None; SQLite foundation is migration-free |
| Trust profile version | `docs/security/TRUST-MODEL.md` (repository commit version) |
| Retention policy version | `docs/data/DATA-FLOW-RETENTION.md` (repository commit version) |
| Test report | [`evidence/AGDA-10/test-report.md`](../../evidence/AGDA-10/test-report.md) |
| Redaction review | PASS; manifest and report contain no tokens, private keys, personal data, or message bodies |
| GitHub source mirror verification | PASS: [`agent/agda-1-foundation`](https://github.com/l-ra/agdatovka/tree/agent/agda-1-foundation) at provider commit `e67b118d35379a082b536a7b4516c1a0b5aa523a`; 68/68 paths match, with executable-bit metadata differences on two fork scripts |
| GitHub integrated-main mirror verification | BLOCKED: local final `main` is `c8793553d2033fd09d043d517006d2ed95f06f95`; published `main` remains provider commit `b29db6ef48cccad060150c8047c1ceaa8a0ac558` (28 files); non-force push failed because GitHub write credentials were unavailable |

This is a synthetic/local integration manifest. It is not a production release
authorization or a claim of external adapter conformance.
