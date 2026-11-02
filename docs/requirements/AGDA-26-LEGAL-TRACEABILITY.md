# AGDA-26 legal and requirements traceability

This register is an engineering traceability artifact for synthetic/test data.
It is not legal advice, a legal-compliance certification, or a tenant retention
schedule. Access dates are UTC: 2026-11-01.

| ID | Official source (title, publisher, date) | Extracted obligation/behavior | Interpretation and implementation choice | Confidence | Unresolved question |
| --- | --- | --- | --- | --- | --- |
| RT-01 | [Act 300/2008 Sb., §17](https://e-sbirka.gov.cz/sb/2008/300), e-Sbírka / Ministry of the Interior, current public text accessed 2026-11-01 | Delivery occurs on authorized login; absent login, statutory fiction occurs on the tenth day, subject to the Act. | Store delivery event type and authoritative timestamps separately. This task does not calculate legal deadlines for a tenant. | High for statutory rule; deployment applicability remains open. | Which tenant-specific procedural rules and exceptions apply to each message class? |
| RT-02 | [Datové schránky help 3.3](https://datovka.gov.cz/info/cs/help/3.3.text.html), Digital and Information Agency, current page accessed 2026-11-01 | Official portal guidance describes ordinary-message deletion after 90 days from login delivery and system-message deletion after 100 days from delivery. | `ag-retention-v1` records these as a versioned reference profile, never as universal law. | High for published service behavior; not a legal opinion. | Does an archive/Datový trezor or different service contract replace the reference clock? |
| RT-03 | [Options for long-term storage](https://datovka.gov.cz/info/cs/2043.html), Digital and Information Agency, current page accessed 2026-11-01 | Users arrange longer-term preservation separately; the page distinguishes the original electronic message from print/conversion options. | Export includes policy, object, event, receipt, tombstone, and trust-profile manifests so preservation is inspectable. | High for published guidance; preservation sufficiency unresolved. | What evidentiary preservation service, if any, is required by the deploying organization? |
| RT-04 | [GDPR Regulation (EU) 2016/679, Articles 5(1)(e), 6(1)(c), 17(3)(e)](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng), European Union, 2016, current text accessed 2026-11-01 | Personal data should not be retained longer than necessary; legal obligations and establishment/exercise/defence of legal claims are relevant exceptions. | Legal hold blocks deletion; policy version, reason, request, tombstone digest, and audit evidence are retained. Controller/processor role is deferred. | High for regulation; deployment-specific application unresolved. | What lawful basis, schedule, hold authority, and access restrictions apply in deployment? |
| RT-05 | [Act 99/2019 Sb.](https://e-sbirka.gov.cz/sb/2019/99), e-Sbírka / Czech Republic, current public text accessed 2026-11-01 | Public-sector websites and mobile applications have accessibility duties subject to scope and exceptions. | Public UI acceptance covers keyboard, semantics, focus, labels, and assistive technology; no certification claim is made here. | High for statute; scope assessment deferred. | Is the eventual operator/interface within the Act's public-sector scope? |

## Requirement-to-evidence map

| Requirement | Implementation | Test/fixture | Evidence and status |
| --- | --- | --- | --- |
| Explicit policy/data class | `RETENTION_POLICY_VERSION`, `RETENTION_POLICY`, export `policy` manifest | `test_legal_hold_blocks_tombstone_and_restore_verifies_export`, `fixtures/retention/policy.json` | Implemented synthetic reference profile |
| Legal hold blocks deletion | `legal_holds`, deletion job guard | same test, 409 assertion | Implemented; legal authority/workflow open |
| Deletion job/tombstone/audit/digest | `retention_deletion_jobs`, `retention_tombstones`, `retention.deleted` audit event | tombstone/job response assertions | Implemented synthetic |
| Export manifests | policy, objects, message events, audit events, holds, tombstones, trust profiles | stable export and restore tests | Implemented synthetic |
| Isolated restore report | namespace validation, manifest/object/event/profile/pending-operation checks, blind replay false | restore success and tamper fail-closed tests | Implemented synthetic; no production restore proof |

## Explicit deferrals

- Exact tenant schedules, controller/processor allocation, legal-hold authority,
  and evidentiary preservation sufficiency require deployment-specific review.
- No source here authorizes production data, real credentials, or a claim that
  this repository is legally compliant.
