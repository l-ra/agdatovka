# Foundation baseline — 2026-10-30

## What changed

Commit [`111597a`](https://github.com/l-ra/agdatovka/commit/111597ade20188581515939177251a8f2c3ff4af) records a source-backed foundation for an independent reimplementation of public data-box interfaces: requirements and traceability, target architecture, a versioned management API contract, trust and synthetic-only security boundaries, data-flow and release rules, and a CZ.NIC Datovka compatibility plan.

## What is proven

The documents are committed and cross-linked. The source register points to official ISDS/CZ.NIC pages, standards, and EU legal sources. The API and architecture are specified for implementation planning. Deferred performance scenarios include a future 1,000-message/minute profile and large-message handling.

## What is not proven yet

No server implementation, public deployment, performance result, legal opinion, or production interoperability claim is made by this milestone. The current ISDS WSDL/XSD package still needs to be pinned, synthetic fixtures need to be implemented, and independent security/QA review remains required.

Migration of existing data is out of scope. No real user accounts, messages, or production credentials are used.

## Agent statement

“The milestone captures source-backed requirements and an implementation-planning contract; implementation and interoperability remain subsequent verification steps.” — factual summary of the foundation author’s committed scope in [`111597a`](https://github.com/l-ra/agdatovka/commit/111597ade20188581515939177251a8f2c3ff4af), not a claim beyond that commit.

## Next reviewable slices

1. Implement the management API, policy model, audit events, and metadata contract with deterministic tests.
2. Implement the streaming content/outbox/message-operation pipeline.
3. Pin the ISDS test profile and build SOAP/WSDL, receipt, trust, and lifecycle fixtures.
4. Build the Datovka fork profile and smoke harness.
5. Run independent threat-model, conformance, and red-team reviews before any release outside a synthetic environment.

Sources and limitations: [`SOURCE-REGISTER.md`](https://github.com/l-ra/agdatovka/blob/111597ade20188581515939177251a8f2c3ff4af/docs/requirements/SOURCE-REGISTER.md), [`LEGAL-REGISTER.md`](https://github.com/l-ra/agdatovka/blob/111597ade20188581515939177251a8f2c3ff4af/docs/requirements/LEGAL-REGISTER.md), and [`PUBLIC-INTERFACES.md`](https://github.com/l-ra/agdatovka/blob/111597ade20188581515939177251a8f2c3ff4af/docs/compatibility/PUBLIC-INTERFACES.md).
