# Legal and evidentiary register

This is an engineering register, not legal advice and not a certification. It
records questions that affect the design and the evidence needed to answer
them. A release may not describe an item as legally compliant unless a current
source, legal review, and reproducible test evidence are linked.

## Register

| ID | Topic | Source | Engineering consequence | Evidence / owner | State |
| --- | --- | --- | --- | --- | --- |
| LEG-01 | Data-box acts, access, delivery, and conversion | S-01; current consolidated text | Model box, user authority, message, delivery event, and receipt as distinct records. Do not infer legal delivery from a UI read. | Legal review + delivery fixture set; Requirements/Legal | Open |
| LEG-02 | Operating rules and technical interface | S-02, S-06 | Version and checksum the rules/WSDL package used by an adapter. Keep old and modern adapters explicit. | Pinned source bundle; ISDS Interoperability | Open |
| LEG-03 | Delivery by login and statutory fiction | S-01, S-04 | Persist event type, authoritative timestamp, source event, time-zone rules, and the rule version. Support weekend/holiday behavior as a fixture, not a hard-coded assumption. | EV0/EV2/EV5/EV11 fixtures; QA | Open |
| LEG-04 | Server retention and Datový trezor distinction | S-05 | Separate reference-server retention from tenant archive policy. Run deletion as an auditable state transition and retain a tombstone/digest where permitted. | Retention clock tests + legal decision; Data/Legal | Open |
| LEG-05 | Personal data protection | S-14 and Czech Act 110/2019 Sb. ([official register](https://e-sbirka.gov.cz/sb/2019/110)) | Minimize identifiers, purpose-bind processing, restrict exports, encrypt content, and define controller/processor responsibilities. | DPIA or documented applicability decision; Security/Legal | Open |
| LEG-06 | Electronic identification, signatures, seals, and timestamps | S-15, S-11, S-13 | Treat trust validation, signing, and timestamping as explicit services with retained evidence. Do not claim qualified status from using a certificate. | Trust validation vectors + legal review; Security | Open |
| LEG-07 | Accessibility and public interface | Official ISDS accessibility guidance at [help/13.0](https://datovka.gov.cz/info/cs/help/13.0.text.html) and Czech Act 99/2019 Sb. | Management UI needs keyboard, semantic, and assistive-technology acceptance tests; accessibility is part of interface compatibility. | Automated plus manual accessibility evidence; QA | Open |
| LEG-08 | Public reporting and disclosure | Project policy in `reporting/README.md` | Publish verified progress and limitations only. Redact credentials, personal data, infrastructure details, and unpublished vulnerabilities. | Reporting review checklist; Public Reporting | Open |

## Legal decision gates

Before a production-like release, the Release Integration Engineer must have
links to decisions for LEG-01 through LEG-06. Until then, public wording is
limited to “designed for”, “tested against”, or “compatible with the recorded
fixture”, as appropriate. “Compliant”, “legally valid”, “qualified”, and
similar claims are prohibited without explicit review evidence.

## Deliberately out of scope

- Migration, import, or cleansing of existing AGDatovka data.
- Real user accounts, production credentials, or real legal messages.
- A legal opinion about a future operator's licensing, controller/processor
  role, statutory records duties, or qualified trust-service status.
