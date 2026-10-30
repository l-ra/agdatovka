# Compatibility boundary

The project preserves the required behavior of public interfaces and workflows
while allowing modern, versioned interfaces alongside them. Compatibility is
implemented through explicit contracts and adapter layers, not by coupling to
the former implementation.

The compatibility matrix will cover authentication, session behavior,
databox creation, message sending, attachments, receipts, lifecycle states,
search, export, errors, trust stores, certificates, and audit evidence.

Every public contract change requires a fixture, a compatibility test, a
versioning decision, and a documented effect on a future migration project.
