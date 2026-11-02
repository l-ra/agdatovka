# ISDS compatibility adapter

`ag_datovka.isds_adapter.IsdsCompatibilityAdapter` is the migration-free,
offline boundary for REQ-004, REQ-005, REQ-012, and REQ-013. It maps synthetic
envelopes, attachments, VoDZ profiles, authentication results, lifecycle
codes, receipts, and upstream errors to append-only `DomainEvent` values.

The source profile is `isds-reference-2026-06-26`; its checksums and URLs are in
the [source manifest](ISDS-SOURCE-MANIFEST.json). Raw receipt bytes are never
replaced by normalized fields: the event carries byte length, base64 raw
evidence, SHA-256, and validation metadata, and exports are derived copies.
Signature, certificate-chain, and declared upstream-error failures are
rejected closed. The adapter has no network client and accepts no
credentials, so existing callers can adopt it without a migration or endpoint
change. A future transport must provide the same synthetic payload shapes.

The event mapping is intentionally additive: `EV0` → `submitted`, `EV2` →
`delivered`, `EV3` → `read`, `EV5` → `statutory_fiction`, `EV6` →
`undeliverable`, `EV8` → `delivery_failed`, and `EV11` → `expired`. Unknown
codes are rejected rather than silently flattened. Upstream error text is
retained only as `safeDetail`, with retryability explicit.
