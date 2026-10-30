# AGDA-16 release integration manifest

## Scope

This manifest records the local Phase 2 integration result for the synthetic,
offline release gate. No production deployment, real data, credentials,
private keys, or external ISDS request was used.

## Provenance

| Item | Exact value |
| --- | --- |
| Integration checkout | `/tmp/agda-10-integration` |
| Integrated branch | `main` |
| Source branch | `agent/agda-1-foundation` |
| Source branch tip | `dce9120b634397d4811c15d6ba033674e5dc9c63` |
| Source prerequisite base | `75782b28324c82d60b2323b7115ce8312fe9a767` |
| Integration method | `git merge --no-ff --no-edit agent/agda-1-foundation` |
| Local integration merge commit | `ec0fd82828a7cd1f02f9ff90c06a6def8b4e3c25` |

The merge preserves the AGDA-13, AGDA-14, and AGDA-15 evidence commits and the
security remediation commit in reviewable local ancestry.

## Gate disposition

The deterministic synthetic/local checks passed. The independent security
review remains adverse for release outside the isolated synthetic/test scope:
concurrent idempotency, malformed attachment metadata, unverifiable caller
supplied attachment digests, and unexecuted performance/compatibility claims
remain release blockers. This manifest makes no production or compliance claim.

## Inputs

- Versioned ISDS, pipeline, API, trust, and fork fixtures.
- `qa/performance-scenarios.json`, `qa/performance-harness.json`, and the
  validation-only readiness command.
- AGDA-14 security review and AGDA-15 compatibility/conformance evidence.
