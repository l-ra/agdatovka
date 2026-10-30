# Management interface — initial contract

The management interface will provide authenticated operations to:

1. create and configure a databox;
2. manage identities, roles, permissions, and authentication methods;
3. send messages and large attachments;
4. observe message lifecycle and delivery receipts;
5. search, export, and audit messages and configuration changes.

Operations must be idempotent where retries are possible. Message content is
handled as a stream or durable object with checksums; metadata and lifecycle
events remain queryable. The contract will define authorization, error codes,
state transitions, audit events, retention, and compatibility versions before
implementation claims are made.
