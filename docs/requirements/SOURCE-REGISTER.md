# Source register

Status: baseline assembled 2026-10-30. This register distinguishes an
authoritative obligation, an observed public behavior, and an AG Datovka 2
design decision. A URL is evidence to inspect; it is not by itself proof that
AG Datovka 2 is compliant.

Access dates are UTC. Dynamic government pages and WSDL packages must be
snapshotted with a checksum when they become test inputs. Never put production
credentials, personal data, or real message content in a snapshot.

The URLs below were checked on 2026-10-30 UTC. “Current” always means the
publisher's version at the recorded access date; it is not a promise that a
dynamic page or technical annex remains unchanged.

## Sources

| ID | Source | Type and use | Initial finding | Evidence status |
| --- | --- | --- | --- | --- |
| S-01 | [Act 300/2008 Sb.](https://e-sbirka.gov.cz/sb/2008/300) | Czech legal source; electronic acts, data boxes, delivery and conversion | Legal baseline for the data-box domain. Exact obligations require legal review against the current consolidated text. | URL recorded; snapshot and legal review pending |
| S-02 | [ISDS Operating Rules, current published page](https://datovka.gov.cz/info/cs/2053.html) | Government operational rules and technical-document entry point | The page states the version effective 2025-06-26 until withdrawal. The linked rules and technical annexes are the compatibility authority. | URL recorded; current annex package must be pinned before adapter implementation |
| S-03 | [ISDS developer test environment](https://datovka.gov.cz/info/cs/help/8.9.text.html) | Official synthetic environment and access procedure | A public test environment exists for external web-service and authentication integration. It uses test identities and can be deleted by its operator. | Procedure recorded; no account or credential acquired |
| S-04 | [ISDS delivery events and receipts help](https://datovka.gov.cz/info/cs/help/5.4.text.html) | Observable lifecycle behavior | Documents EV0/EV2/EV3/EV5/EV6/EV8/EV11 semantics, delivery by login/fikce, and receipt detail. | Behavior captured; fixture scenarios required |
| S-05 | [ISDS retention help](https://datovka.gov.cz/info/cs/help/3.3.text.html) and [glossary](https://datovka.gov.cz/info/cs/1054.html) | Observable retention behavior | Published help describes 90 days after delivery by login for ordinary messages, 100 days from delivery for system messages, and the Datový trezor exception. | Behavior captured; legal interpretation and exact clock tests required |
| S-06 | [ISDS VoDZ rules](https://datovka.gov.cz/info/cs/2037.html) | Large-message and attachment compatibility | The page describes a 100 MB VoDZ limit in the 2024 rules, a `ws2` endpoint, named large-message methods, allowed formats, and a 50-attachment limit. Treat this as a versioned reference, not a permanent product limit. | URL recorded; exact current annex/WSDL must be pinned |
| S-07 | [CZ.NIC Datovka](https://www.datovka.cz/cs/index2.html) | Reference client behavior and workflow | Desktop client supports local retention, verification, receipts, export, import, search, multiple boxes, restricted users, CLI/API functions, and large messages. | Behavior inventory captured; black-box fixtures required |
| S-08 | [CZ.NIC libdatovka](https://www.datovka.cz/cs/pages/libdatovka.html) | Reference adapter/library and license boundary | The library exposes ISDS access for third-party applications, is written in C, is LGPLv3, and has its own evolving interface. It is a reference/integration target, not an AG runtime dependency. | URL and license noted; fork policy required |
| S-09 | [RFC 9110 HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110) | Modern API transport semantics | Defines HTTP method, status, conditional request, and representation semantics used by the versioned management API. | Normative reference |
| S-10 | [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457) | Error representation | Defines machine-readable error details for HTTP APIs. | Normative reference |
| S-11 | [RFC 5280 PKIX certificate profile](https://www.rfc-editor.org/rfc/rfc5280) | X.509 chain and revocation validation | Provides the certificate and CRL profile used by the trust model. | Normative reference |
| S-12 | [RFC 8446 TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446) | Transport security | Defines the TLS 1.3 handshake, certificate authentication, and AEAD protected records. | Normative reference |
| S-13 | [RFC 3161 time-stamp protocol](https://www.rfc-editor.org/rfc/rfc3161) | Evidence timestamping | Defines the protocol boundary for trusted timestamps over evidence digests. | Normative reference; service selection pending |
| S-14 | [GDPR, Regulation (EU) 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng) | Personal-data processing baseline | Requires purpose limitation, minimization, security, retention governance, and demonstrable controls; the exact controller/processor roles remain a legal decision. | Legal source recorded; DPIA/legal review pending |
| S-15 | [eIDAS, Regulation (EU) No 910/2014](https://eur-lex.europa.eu/eli/reg/2014/910/oj/eng) | Electronic identification and trust services | Relevant when choosing qualified signatures, seals, timestamps, or trust-service integrations. No qualified-service claim is made by this project. | Legal source recorded; applicability review pending |
| S-16 | [CZ.NIC Datovka source project](https://gitlab.nic.cz/datovka/datovka) | Fork provenance and source inspection | The public GitLab project is the upstream desktop project referenced by the Datovka website. | URL recorded; license and commit pin required before fork |

## Evidence rules

1. Cite a source ID in requirements, decisions, tests, and reports. Include the
   URL and access date in the source register.
2. For a dynamic page, record the retrieved URL, retrieval timestamp, SHA-256
   of any fixture or PDF, and the source version shown by the publisher.
3. Keep an observed behavior separate from a legal requirement. A Datovka
   feature is compatibility evidence, not an obligation on the new service.
4. Keep an implementation interpretation separate from both. Interpretations
   need a decision-log entry and a conformance test.
5. If sources conflict or a rule is ambiguous, record the conflict and stop
   any compliance claim until legal or interoperability review resolves it.

## Open source and legal questions

- Confirm the exact consolidated text and applicability of Act 300/2008 and
  related Czech rules before making any delivery, retention, or evidentiary
  claim.
- Pin the current ISDS Operating Rules technical annexes and WSDL/XSD files;
  the public page can change without changing this repository commit.
- Record the exact upstream Datovka/libdatovka commit and license notices before
  creating a fork. The fork is a compatibility tool and must remain separate
  from the standalone service implementation.
- Decide, with legal counsel, whether a deployed instance is a controller,
  processor, or another role for each tenant and integration mode.
