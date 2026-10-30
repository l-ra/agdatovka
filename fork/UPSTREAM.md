# CZ.NIC Datovka fork provenance

This directory is a compatibility artifact only. It is not imported by
`ag_datovka`, is not a server runtime dependency, and contains no former
AGDatovka code or data.

## Pinned source

| Field | Value |
| --- | --- |
| Upstream | `https://gitlab.nic.cz/datovka/datovka.git` |
| Pinned ref | `master` |
| Pinned commit | `67f1f23056e6f96e4a93632c11418a8ce8ca0b2f` |
| Retrieved | 2026-10-30 (UTC) |
| Retrieval check | `git ls-remote https://gitlab.nic.cz/datovka/datovka.git HEAD` |
| Local boundary | `fork/` |

To materialize the source for a local build, use a disposable checkout and
verify the commit before applying the local patch:

```sh
git clone https://gitlab.nic.cz/datovka/datovka.git /tmp/datovka-upstream
git -C /tmp/datovka-upstream checkout --detach 67f1f23056e6f96e4a93632c11418a8ce8ca0b2f
git -C /tmp/datovka-upstream rev-parse HEAD
git -C /tmp/datovka-upstream apply "$PWD/fork/patches/0001-endpoint-profile-layer.patch"
```

The smoke harness does not clone or contact an endpoint by default. Network
builds and public-test runs are explicit operator actions.

## License and notice inventory

The upstream checkout must be reviewed at the pinned commit before a binary
redistribution. Preserve every upstream `LICENSE*`, `COPYING*`, `NOTICE*`,
copyright header, and third-party notice in the checkout. The expected
inventory for this compatibility fork is:

| Component | Boundary | Required notice/license review |
| --- | --- | --- |
| Datovka desktop | application | upstream repository license and notices |
| libdatovka | linked ISDS client library | LGPLv3 and its bundled notices |
| Qt and Qt modules | desktop toolkit | applicable Qt license and source-offer terms |
| system/package dependencies | build/runtime environment | distribution package licenses |

No dependency is copied into this repository. `fork/NOTICE` records the
attribution and the local patch boundary; it is not a substitute for the
upstream notices in a distributable checkout.

## Updating the pin

An update must record the new full commit, rerun the license inventory and
`fork/scripts/smoke.py`, review the patch for context drift, and update the
evidence README. Never replace the pin with a branch or a floating download.
