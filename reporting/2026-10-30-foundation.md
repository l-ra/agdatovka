# Foundation baseline — 2026-10-30

## What changed

AG Datovka 2 now has a source-backed foundation for an independent
reimplementation of public data-box interfaces. The repository records:

- requirements, legal questions, and source-to-test traceability;
- a target architecture for asynchronous delivery, large content, audit
  evidence, backpressure, horizontal workers, and a future 1,000-message/minute
  scenario;
- a versioned management API contract for boxes, identities, roles, messages,
  receipts, search, exports, operations, and audit;
- a certificate/key/trust boundary and synthetic-only security model;
- data-flow, retention, restore, and release rules;
- a CZ.NIC Datovka compatibility and desktop-fork plan; and
- deferred performance scenarios with fixtures, metrics, limits, and stop rules.

## What is proven

The documents are committed and cross-linked. The source register points to
official ISDS/CZ.NIC pages, standards, and EU legal sources. The API and
architecture are specified for implementation planning.

## What is not proven yet

No server implementation, public deployment, performance run, legal opinion,
or production interoperability claim is made by this milestone. The current
ISDS WSDL/XSD package still needs to be pinned, synthetic fixtures need to be
implemented, and independent security/QA review remains required.

Migration of existing data is out of scope. No real user accounts, messages,
or production credentials are used.

## Next reviewable slices

1. Implement the management API, policy model, audit events, and metadata
   contract with deterministic tests.
2. Implement the streaming content/outbox/message-operation pipeline.
3. Pin the ISDS test profile and build SOAP/WSDL, receipt, trust, and lifecycle
   fixtures.
4. Build the Datovka fork profile and smoke harness.
5. Run independent threat-model, conformance, and red-team reviews before any
   release outside a synthetic environment.

Sources and limitations: `docs/requirements/SOURCE-REGISTER.md`,
`docs/requirements/LEGAL-REGISTER.md`, and
`docs/compatibility/PUBLIC-INTERFACES.md`.
