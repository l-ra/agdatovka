# Public project reporting

The Public Reporting Agent updates this material after significant milestones,
decisions, integrations, and risk discoveries. Updates are event-driven, not
time-based. They explain progress in human language, state what is proven and
what remains uncertain, and include short factual statements from responsible
agents.

The generated public site is mirrored to the `reporting` branch and served by
GitHub Pages. Secrets, personal data, private infrastructure, unpublished
vulnerabilities, and unsupported compliance claims must never appear here.

## Publication checklist

- Link the exact Git commit and source/fixture identifiers supporting each
  factual statement.
- Separate `implemented`, `specified`, `tested`, `deferred`, and `unknown`.
- State that migration is out of scope and that test environments are
  synthetic unless a separate approved scope says otherwise.
- Remove credentials, certificate private keys, personal data, private URLs,
  detailed exploit steps, and unsupported legal/compliance language.
- Have the responsible engineering/review agent check the technical wording;
  the Public Reporting Agent owns the public presentation.

## Milestone cadence

Publish on a significant baseline, implementation slice, integration, decision,
or risk discovery. Do not publish a timer-driven status update with no verified
change. Short interviews must be factual, approved for publication, and never
expose private task context or secrets.
