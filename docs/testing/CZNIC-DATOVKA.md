# CZ.NIC Datovka compatibility plan

The open-source CZ.NIC Datovka desktop application is the reference workflow
client. The [Datovka site](https://www.datovka.cz/cs/index2.html) describes the
desktop features and the [libdatovka page](https://www.datovka.cz/cs/pages/libdatovka.html)
describes the ISDS access library and its LGPLv3 boundary. The upstream project
is inspected and forked only as an interoperability test artifact; it is not a
runtime dependency of AG Datovka 2.

## Baseline workflow inventory

The fork must exercise, with synthetic data, multiple boxes and restricted
users, login/configuration, incoming and outgoing messages, attachment
streaming, receipt verification, lifecycle display, search, export/import of
fixture ZFO, local retention, large-message profile selection, and CLI/API
smoke paths where the upstream build exposes them. Each workflow maps to a row
in `docs/compatibility/PUBLIC-INTERFACES.md` and a REQ ID.

## Test profiles

| Profile | Endpoint | Credentials | Purpose |
| --- | --- | --- | --- |
| `ag-synthetic` | Local/isolated AG endpoint | Generated test identity/certificates | Verify the new implementation and modern API adapter |
| `isds-public-test` | Official public test environment described in S-03 | Explicitly provisioned synthetic account only | Compare the reference client and current public behavior |
| `offline-fixture` | No network | Checked-in non-secret fixture data | Parser, receipt, search, export, and failure tests |

Profiles are selected in an external test configuration. The default profile
is `offline-fixture`; production hostnames are rejected by a preflight check.

## Source and license controls

Before forking, record the upstream repository URL, commit/tag, license files,
submodule/dependency licenses, and checksum of the source archive. Preserve
copyright and license notices. Keep the fork in a clearly named compatibility
boundary and document every local patch. The AG service source must not import
the fork or libdatovka as a production dependency.

## Evidence and limitations

Every run stores profile, upstream commit, AG commit, fixture IDs, versioned
configuration, command, UTC timestamps, and redacted logs. Differences are
classified as upstream-version difference, unsupported operation, intentional
modern API behavior, defect, or unresolved question. Real accounts, real
messages, production credentials, and unapproved public endpoints are out of
scope.
