# Datovka fork build and smoke evidence

The fork is separate from the AG server runtime. Run commands from the
repository root. The default path is deterministic and offline.

## Build the pinned desktop checkout

```sh
git clone https://gitlab.nic.cz/datovka/datovka.git /tmp/datovka-upstream
git -C /tmp/datovka-upstream checkout --detach 67f1f23056e6f96e4a93632c11418a8ce8ca0b2f
git -C /tmp/datovka-upstream apply "$PWD/fork/patches/0001-endpoint-profile-layer.patch"
# Follow the upstream build instructions for the host OS/toolchain.
```

The patch is kept as a local review artifact; the exact upstream build is
intentionally not run in CI because Qt/libdatovka toolchains are platform
specific. A binary build must retain upstream notices listed in `UPSTREAM.md`.

## Preflight and smoke

```sh
fork/scripts/check.sh
python3 fork/scripts/smoke.py --profile offline-fixture
```

`check.sh` validates all three profiles without contacting a network. The two
network profiles must remain placeholders until a separately approved,
synthetic environment is provisioned. Then launch the materialized desktop
checkout with the selected profile and capture only redacted logs:

```sh
DATOVKA_PROFILE=fork/profiles/ag-synthetic.yaml <upstream-build-command>
DATOVKA_PROFILE=fork/profiles/isds-public-test.yaml <upstream-build-command>
```

Never place values for credential references, client keys, or passwords in the
profile files. Inject them through the approved test secret store. Production
hosts are forbidden by preflight.

## Workflow matrix

| Profile | Network | Required workflow | Evidence |
| --- | --- | --- | --- |
| offline-fixture | no | parse, receipt, search, export | JSON result from smoke.py |
| ag-synthetic | isolated test only | login, send, retrieve, lifecycle, search, export | redacted run manifest and fixture IDs |
| isds-public-test | approved public test only | read-only comparison plus message workflow | approval reference and redacted logs |

## Teardown and evidence

Stop the disposable endpoint, delete its temporary store and client session,
and publish a redacted manifest containing profile, pinned commit, AG commit,
fixture IDs, command, UTC timestamps, and result. Do not publish credentials,
private keys, message content from real accounts, or raw personal data.
