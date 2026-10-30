# ISDS adapter evidence

Date: 2026-10-30 UTC  
Source profile: `isds-reference-2026-06-26`  
Fixtures: synthetic only

## Conformance result

`python -m unittest tests.test_isds_adapter` covers envelope and attachment
digests, the VoDZ boundary (100 MiB/50 attachments and `ws2`), authentication
responses, all required EV0/EV2/EV3/EV5/EV6/EV8/EV11 mappings, immutable receipt
digest metadata, XML/ZFO/JSON exports, upstream retryability, malformed payloads,
and the fixture secret boundary.

The adapter is offline and does not create a production endpoint, import
historical data, use a credential, or alter the existing v1 management API.
The pinned source checksums are in
`docs/compatibility/ISDS-SOURCE-MANIFEST.json`.
