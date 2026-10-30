# Datovka desktop fork plan

This is a separate compatibility artifact, not a continuation of the former
AGDatovka implementation and not part of the server runtime. It will make the
reference desktop workflow reproducible against the standalone implementation
and the official synthetic/reference environment.

## Fork boundary

1. Fork the upstream CZ.NIC Datovka source at a recorded commit/tag after
   license and dependency review.
2. Preserve upstream notices and keep local changes small, reviewable, and
   labelled `ag-datovka-compat`.
3. Add an endpoint-profile layer or configuration patch that changes only the
   base endpoint, trust store, test credentials, and feature profile.
4. Do not copy server code, former AGDatovka data, production credentials, or
   private keys into the fork.

## Required deliverables

- `fork/UPSTREAM.md`: upstream URL, commit, license/dependency inventory,
  patch list, and update procedure.
- `fork/profiles/ag-synthetic.*` and `fork/profiles/isds-public-test.*`: sample
  templates with placeholders only; production profiles are prohibited.
- `fork/SMOKE-TEST.md`: build/run commands, synthetic setup, workflow matrix,
  expected evidence, and teardown.
- CI job that rejects production hostnames, secret patterns, and unpinned
  upstream changes.

## Smoke workflow

1. Start the isolated AG endpoint and load the synthetic trust profile.
2. Configure one fake sender box and one fake recipient box.
3. Launch the fork with `ag-synthetic`, send a small message, retrieve it,
   inspect lifecycle/receipt, search it, and export its evidence.
4. Repeat read-only comparison with `isds-public-test` when an approved,
   synthetic account exists.
5. Run the offline parser/export fixtures.
6. Remove the disposable store and publish only redacted manifests.

The fork is complete only when both endpoint profiles are documented, the AG
profile does not silently point at production, and a reviewer can reproduce
the smoke result from the recorded upstream commit.
