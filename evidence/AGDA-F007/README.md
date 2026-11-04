# AGDA-F007 sender-identity authorization remediation

The message-draft endpoint now binds a declared `senderIdentityId` to the
authenticated tenant identity. Same-tenant membership is insufficient: a
caller selecting another active identity receives a non-leaking HTTP 403 with
`sender_identity_forbidden`, and no message row is created. The authorization
audit event records the authenticated actor identity, declared sender identity,
authorization basis, and decision. The platform control-plane fixture remains
explicitly auditable, while drafts with no declared sender remain supported.

Focused regression and positive-path verification:

```text
$ python3 -m unittest tests.test_management_api.ManagementApiTest.test_cross_tenant_identity_references_are_rejected tests.test_management_api.ManagementApiTest.test_same_tenant_sender_impersonation_is_rejected_and_audited tests.test_user_app.UserAppTest.test_additive_session_read_and_download_contract
...
----------------------------------------------------------------------
Ran 3 tests in 0.009s

OK
```

Full regression verification:

```text
$ python3 -m unittest discover -v
...
----------------------------------------------------------------------
Ran 69 tests in 0.618s

OK
```

This is synthetic local-fixture evidence. It does not certify production
identity providers, ISDS endpoints, deployment, or performance.
