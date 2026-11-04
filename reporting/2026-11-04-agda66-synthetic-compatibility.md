# Synthetic public-interface compatibility milestone — 2026-11-04

## Milestone summary

The AG Datovka 2 compatibility slice is now recorded in commit
[`678d632`](https://github.com/l-ra/agdatovka/commit/678d6327987c7b05632f0fefc9813bb33a77a525).
It adds conformance evidence for a synthetic SOAP/WSDL gateway and its
authentication and trust boundary, while retaining the synthetic Datovka fork
workflow and the previously implemented adapter fixtures.

The repository verification run passed **91 tests** and `git diff --check`.
The detailed evidence is the
[`AGDA-62 evidence report`](https://github.com/l-ra/agdatovka/blob/678d6327987c7b05632f0fefc9813bb33a77a525/evidence/AGDA-62/README.md),
including the focused SOAP/auth suites, lifecycle event mapping, receipt
provenance, VoDZ boundary checks, retry/idempotency evidence, and management
API regression coverage.

## What is implemented and tested

- A synthetic SOAP/WSDL gateway checks the pinned operation surface, envelope
  shape, SOAP actions, correlation, attachment encoding, and structured faults.
- The synthetic authentication/trust boundary fails closed for expiry,
  hostname, key-usage, revocation, chain/CA, identity-binding, nonce,
  endpoint, and secret-handle failures.
- Synthetic receipt bytes remain round-trippable and digestable, and lifecycle
  mappings reject unmapped event codes instead of silently normalizing them.
- The Datovka fork workflow, bounded local content boundary, retry/recovery
  path, and existing management API regressions remain covered by repository
  tests.

These are repository-native tests against versioned fixtures. They do not
represent live provider traffic.

## Explicit limitations

All endpoints, identities, certificates, receipts, message IDs, and payloads in
this milestone are **synthetic**. No live ISDS endpoint, production credential,
real user data, or production release was used.

The WSDL/XSD and protocol semantics are synthetic, versioned fixtures. The
gateway does not perform a live TLS handshake, certificate exchange, XML
signature verification, or provider delivery, so this evidence is **not a
claim of official or live ISDS conformance**. The VoDZ checks exercise adapter
metadata and the bounded local boundary; they are not a 100 MiB network
benchmark.

Performance execution remains **deferred**. No load, latency, throughput,
capacity, or SLO measurement ran; the future scenarios remain hypotheses in
the repository. Migration of existing data is out of scope.

## Current review gate

Independent adverse review **AGDA-64** remains active. Release integration and
GitHub mirror verification **AGDA-65** remain pending. This milestone is
therefore a synthetic compatibility implementation/evidence update, not a
release approval.

## Factual agent statement

**AGDA-62 compatibility evidence statement:** “This is compatibility evidence
for the implemented fixture boundary, not a claim of official or live ISDS
conformance.” This statement is taken from the committed
[`AGDA-62 evidence`](https://github.com/l-ra/agdatovka/blob/678d6327987c7b05632f0fefc9813bb33a77a525/evidence/AGDA-62/README.md)
and does not extend its scope.

## Next verifiable steps

Complete the independent adverse review and release-integration/mirror gates,
then run separately approved synthetic performance scenarios. Any future
provider or production claim requires new, explicitly scoped evidence.
