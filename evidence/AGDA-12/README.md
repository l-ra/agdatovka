# AGDA-12 tenant-isolation remediation evidence

This evidence is synthetic and contains no production data, credentials, or
private findings.

## Scope

- Tenant-scoped callers cannot mutate global roles, permissions, trust
  profiles, or endpoint profiles.
- Tenant-scoped callers cannot assign the `platform-admin` role.
- `auth-methods.identityId` and `messages.senderIdentityId` must reference an
  active identity in the request box.
- Denials use stable problem responses and are recorded in the tenant audit
  stream without leaking credentials or content.

## Verification

Run `python3 -m unittest discover -s tests -v`.

The focused regressions are
`test_tenant_cannot_mutate_global_policy_or_assign_platform_role` and
`test_cross_tenant_identity_references_are_rejected` in
`tests/test_management_api.py`.

## Threat-model conclusion

The prior high findings were caused by tenant permission checks on global
policy routes and unchecked identity foreign references. The remediation adds
platform-only authorization for global policy and an explicit same-box active
identity lookup before persistence. Existing compatibility `dev:` tokens and
modern expiring `oidc:` tokens retain their separate authentication paths;
both remain subject to these authorization checks.
