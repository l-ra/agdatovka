# End-user databox application contract

The end-user application is the static application under `ui/user/`. It is a
separate product surface from the operator/management console under `ui/`.
Both use the existing `/api/v1` contract and synthetic data only.

`GET /api/v1/session` validates the bearer session and returns the bound
identity and tenant. `GET /api/v1/boxes` supplies authorized boxes.
`GET /api/v1/messages/{id}` includes scoped `readAt`; `PATCH
/api/v1/messages/{id}/read` records `{ "read": true|false }` and an audit
event. Attachment retrieval is additive at
`GET /api/v1/messages/{id}/attachments/{attachmentId}` and returns verified
metadata plus base64 bytes for the dependency-free synthetic app. Existing
message, lifecycle, receipt, export, error, and idempotency fields are
unchanged. The additive read-state table uses `IF NOT EXISTS`, so no data
migration is required.
