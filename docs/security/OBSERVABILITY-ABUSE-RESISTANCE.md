# Observability abuse resistance

The offline fixture emits structured metadata only. Request, correlation, and
operation IDs are bounded opaque identifiers. Redaction is applied by field
name and to bearer/private-key markers; content, payload, body, raw XML, raw
bytes, and secret-like fields cannot enter emitted records.

Success traces use deterministic sampling (5% by default). Error, denied,
dead-letter, and forced diagnostic traces bypass sampling. Queue metrics retain
counts for enqueue/claim/retry/completion/dead-letter/backpressure and worker
telemetry adds attempt count and latency. Alert conditions are raised for any
dead letter or backpressure event in the synthetic policy.

Audit records use a SHA-256 previous-digest chain. Verification fails closed
when an event or link is modified; rebuild is tested only against the resulting
offline event set. This provides tamper/rebuild test coverage, not an
immutability guarantee for a production store.

Authorization negative tests cover tenant isolation and platform-only global
policy changes. Legacy `dev:` tokens remain a synthetic compatibility fixture;
modern OIDC-shaped tokens continue through the existing scoped-auth boundary.
