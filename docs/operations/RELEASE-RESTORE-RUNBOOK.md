# Release and restore runbook

This runbook describes reviewable local integration and recovery. It does not
authorize production release or real-data access.

## Release gate

1. Confirm the branch contains source, tests/fixtures, requirements,
   evidence/decision updates, and a sanitized public report.
2. Run contract, unit, security, secret-scan, compatibility, and documentation
   checks. Performance scenarios are checked for completeness but not executed.
3. Confirm the exact commit and source URLs are pushed to the GitHub mirror.
4. Hand the task to the Release Integration Engineer. Only that role performs
   the local `git merge --no-ff` into the integration checkout, preserving
   branch provenance. The implementation owner does not merge their own branch.
5. Record merge commit, source commit, test commands/results, work-product
   links, and mirror verification in the Paperclip task.
6. A release outside a synthetic/test environment requires the appropriate
   security/legal/board gates and is a separate task.

## Release artifact manifest

The release manifest must contain source commit, merge commit, schema/API
version, adapter profile/WSDL checksums, fixture version, image/package
digests, database migration identifier (if any), trust profile versions,
retention policy version, test report links, and redaction review. It must not
contain tokens, private keys, personal data, or full message bodies.

## Backup and restore

1. Quiesce new work or record a consistent snapshot boundary; do not stop
   workers without accounting for leases and outbox records.
2. Export encrypted metadata, content manifest, immutable events, trust profile
   metadata, and policy versions. Secrets are referenced by secret-store IDs,
   never exported as values.
3. Verify checksums and record the manifest before copying to the backup store.
4. Restore into an isolated namespace. Verify object digests, event hash links,
   schema version, profile checksums, and retention/legal holds.
5. Run read-only authorization, search, receipt validation, and queue/outbox
   reconciliation tests. Keep external adapter calls disabled.
6. Rehydrate only idempotent pending operations after review; never replay a
   send blindly. A replay must check operation and adapter idempotency state.
7. Enable traffic only after the restore report is signed/approved under the
   deployment policy. Record the exact restore and verification commits.

## Failure handling

- If a mirror push, checksum, test, or merge verification fails, mark the
  release block explicitly and do not invent a link or SHA.
- If evidence conflicts, preserve both artifacts, open a decision, and stop
  release claims until resolved.
- If secrets or personal data appear in a work product, stop publication,
  revoke/rotate the affected credential if real, and use the security incident
  path. Do not delete the evidence before the incident owner records the scope.
