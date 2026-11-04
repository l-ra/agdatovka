# AGDA-29 — CZ.NIC Datovka fork and local synthetic workflow

This evidence is synthetic-only. It does not prove production compatibility,
public-test interoperability, or delivery to a real databox.

## Reproduction

```sh
fork/scripts/check.sh
python3 fork/scripts/local_workflow.py --manifest /tmp/agda-29-manifest.json
```

The workflow creates a disposable SQLite store, configures a test box and
certificate metadata, sends a base64 fixture attachment, runs the explicit
synthetic worker, retrieves lifecycle and receipt evidence, searches the
message, and exports the manifest. The worker seam is in-process and has no
network path. The temporary store is removed by the process teardown.

The redacted run manifest records the profile, fixture IDs, workflow results,
upstream and AG commits, timestamps, and export digest. It intentionally excludes generated IDs,
message content, credentials, and key material.

The checked-in [`run-manifest.json`](run-manifest.json) is one redacted local
run record; rerunning the command produces a fresh timestamp and digest.

## Compatibility classification

| Surface | Result | Classification |
| --- | --- | --- |
| login/configuration | pass | intentional synthetic API boundary |
| send/retrieve | pass | intentional synthetic API boundary |
| lifecycle/receipt | pass | intentional `ag-synthetic-v1` worker evidence |
| search/export | pass | intentional synthetic API boundary |
| upstream desktop build | documented only | platform-specific Qt/libdatovka toolchain |
| public-test profile | placeholder only | no approved network run |

Pinned upstream source, notices, and the endpoint-profile patch are documented
in [`fork/UPSTREAM.md`](../../fork/UPSTREAM.md), [`fork/NOTICE`](../../fork/NOTICE),
and [`fork/patches/0001-endpoint-profile-layer.patch`](../../fork/patches/0001-endpoint-profile-layer.patch).
