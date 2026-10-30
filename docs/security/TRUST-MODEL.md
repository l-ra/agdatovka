# Security and trust model

This model sets boundaries for the synthetic/test deployment. It is not a
security certification or a claim that the future operator satisfies a legal
standard.

## Trust zones

```text
[caller / UI / fork]
       | TLS + caller auth
[API edge] -- rate limits, request IDs, admission
       | authenticated service calls
[control plane] -- authorization/policy
       |              |
[metadata + audit]  [content store]
       |
[outbox/queue] -> [adapter worker] -- outbound TLS/mTLS -> [named test endpoint]
                          |
                    [trust profile + key handle]
```

The adapter worker is a separate trust boundary because it can cause an
external message side effect. It may read only the content and credentials
needed for a scoped operation. The management API never receives a private key
back in a response.

## Authentication and authorization

1. **Management callers:** OIDC or another explicitly selected modern method
   establishes a subject. Short-lived scoped access tokens carry tenant and
   permission context; refresh/revocation is handled by the identity provider.
2. **Service-to-service:** mTLS or workload identity authenticates a service;
   authorization still comes from the service policy and operation scope.
3. **Reference adapter:** Each synthetic box/profile has its own configured
   credentials or client certificate. Credentials are injected from a secret
   store at runtime and are never committed, logged, or embedded in fixtures.
4. **Break-glass:** Requires a separate capability, expiry, reason, and audit
   event. It cannot be used in default CI.

Authentication proves who/what is calling. Authorization decides what it may
do. Possession of a client certificate, box identifier, or upstream username
does not grant AG management permissions.

## Certificate and key boundary

| Object | Stores | Does not store | Controls |
| --- | --- | --- | --- |
| Trust profile | Anchor fingerprints, allowed issuers, hostname/SAN policy, algorithm policy, profile version | Private key, tenant role | Which peers may be trusted |
| Client certificate record | Public certificate, serial, subject, expiry, key-usage, profile reference | Private key material | Which identity binding is presented |
| Private-key handle | Secret-store/HSM reference, rotation state | Plaintext key in application DB/logs | Signing/mTLS operation access |
| Endpoint profile | Scheme, hostname allow-list, WSDL/XSD checksum, source version | Credentials and arbitrary redirect target | Where an adapter may connect |
| Authorization binding | Subject/certificate fingerprint, tenant, roles, expiry | Trust anchor authority | What the authenticated identity may do |

Certificate validation follows RFC 5280 path, validity, key usage, name, and
revocation policy. Transport uses TLS policy based on RFC 8446 and explicitly
rejects unexpected hostname/profile changes. Certificate renewal is a staged
operation: add new key/cert, validate a synthetic handshake, switch, observe,
then revoke/remove the old binding after its evidence window.

## Synthetic trust store

The repository will contain only public test certificates/keys generated for
fixtures, clearly marked `TEST ONLY`, or certificate metadata without keys.
The test trust store must include:

- valid chain and valid mTLS client certificate;
- expired certificate, not-yet-valid certificate, wrong hostname/SAN,
  wrong key usage, wrong issuer, revoked certificate, and unknown CA;
- rotation overlap and endpoint-profile mismatch;
- malformed certificate and invalid signature cases.

CI fails if a fixture targets a production hostname or contains a secret-like
value. Real user accounts and production credentials are never test fixtures.

## Threat model (initial)

| Threat | Control | Evidence |
| --- | --- | --- |
| Stolen management token | Short expiry, audience/tenant scope, revocation, rate limit, audit | Token abuse test |
| Replay of send request | Idempotency key bound to canonical request and tenant; operation lease | Replay/fault test |
| Duplicate external send after worker crash | Outbox, external idempotency mapping where available, attempt/evidence reconciliation | Crash/restart scenario |
| Wrong tenant access | Server-side policy on every read/write/export; no caller-supplied tenant trust | Cross-tenant negative tests |
| Trust-store substitution | Checksummed named profile, hostname policy, reviewable rotation | Profile tamper test |
| Private-key exfiltration | Secret store handle, no plaintext logs/files, least-privilege worker | Secret scan and access audit |
| Attachment malware or parser abuse | Size/type policy, streaming limits, quarantine/scanning hook, no inline execution | Malformed and decompression-bomb fixtures |
| Evidence tampering | Append-only hash links, raw source retention, timestamp/digest manifest | Tamper/rebuild test |
| Queue overload | Admission limits, per-tenant quotas, backpressure, dead-letter review | Burst scenario |
| Sensitive observability data | Redacted structured logs, digest instead of content, access-controlled traces | Log redaction test |

## Required security review

Independent red-team review must inspect this model, the API authorization
contract, the trust fixtures, content handling, and public reporting before a
release outside synthetic/test environments. Findings are accepted as a
separate review task; adverse findings are completed findings, not silently
converted into approval.

## Implemented boundary (AGDA-6)

The local implementation persists trust profiles, endpoint profiles, and
secret-store key handles as separate records. Trust profiles require pinned
SHA-256 anchor fingerprints, issuers, SAN hostnames, key usage, and an explicit
revocation policy. Endpoint profiles accept HTTPS only when the exact hostname
is allow-listed; credentials and unsafe ports are rejected. Key records contain
only `vault:`, `hsm:`, or `kms:` handles, never private key material.

Certificate validation fails closed for incomplete/unverified chains, expired
certificates, wrong SAN, wrong key usage, revoked status, and unknown issuers.
The `oidc:` caller token is a modern integration point with expiry and tenant
scope; the existing `dev:` token remains a compatibility-only synthetic path.
Both paths still require database membership and permission checks.

## Tenant-isolation remediation (AGDA-12)

Global policy resources are now a platform control-plane boundary: tenant
owners and other tenant-scoped subjects cannot create or enumerate global
roles, permissions, trust profiles, or endpoint profiles. Membership changes
also cannot assign the `platform-admin` role from a tenant scope. These checks
are enforced at each route boundary and are independent of caller-supplied
`boxId` values.

Identity-bearing references are fail-closed. Authentication method bindings
and message sender identities must resolve to an active identity belonging to
the request's box; a reference from another box returns the stable
`cross_tenant_reference` problem with a field error and creates a denied
authorization audit record. Recipient `targetBoxId` remains a deliberate
cross-tenant message-routing field and is not treated as an identity binding.

Regression evidence is in the two focused tests in `tests/test_management_api.py`:
`test_tenant_cannot_mutate_global_policy_or_assign_platform_role` and
`test_cross_tenant_identity_references_are_rejected`.

`fixtures/security/trust-vectors.json` contains certificate facts only and
includes valid, expired, wrong-host, wrong-usage, revoked, and unknown-CA
cases. Audit remains append-only and digest-linked without recording tokens or
key material.
