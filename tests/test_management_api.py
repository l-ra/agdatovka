import json
import tempfile
import unittest

from ag_datovka import create_app


class ManagementApiTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(":memory:")
        self.key_number = 0

    def tearDown(self):
        self.app.close()

    def call(self, method, path, body=None, *, token="dev:platform", key=None):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            self.key_number += 1
            headers["Idempotency-Key"] = key or f"test-{self.key_number}"
        status, response_headers, raw = self.app.handle_request(method, path, headers, body or {})
        return status, response_headers, json.loads(raw)

    def create_box(self, name="Synthetic box"):
        status, _, data = self.call("POST", "/api/v1/boxes", {"name": name, "kind": "test"})
        self.assertEqual(status, 201)
        return data

    def test_create_box_replay_and_idempotency_conflict(self):
        first_status, first_headers, first = self.call("POST", "/api/v1/boxes", {"name": "Replay box"}, key="box-replay")
        replay_status, replay_headers, replay = self.call("POST", "/api/v1/boxes", {"name": "Replay box"}, key="box-replay")
        conflict_status, _, conflict = self.call("POST", "/api/v1/boxes", {"name": "Different"}, key="box-replay")

        self.assertEqual(first_status, 201)
        self.assertEqual(replay_status, 201)
        self.assertEqual(first["id"], replay["id"])
        self.assertEqual(replay_headers["idempotent-replay"], "true")
        self.assertEqual(conflict_status, 409)
        self.assertEqual(conflict["code"], "idempotency_conflict")

    def test_tenant_isolation_and_denied_policy(self):
        first = self.create_box("Tenant one")
        second = self.create_box("Tenant two")
        identity_status, _, identity = self.call("POST", f"/api/v1/boxes/{first['id']}/identities", {"subject": "operator-1", "displayName": "Operator"}, key="identity-1")
        self.assertEqual(identity_status, 201)
        member_status, _, membership = self.call("PUT", f"/api/v1/boxes/{first['id']}/members/{identity['id']}", {"role": "box-operator"}, key="member-1")
        self.assertEqual(member_status, 200)
        operator_token = f"dev:{first['id']}:{identity['id']}"

        status, _, problem = self.call("GET", f"/api/v1/boxes/{second['id']}", token=operator_token)
        self.assertEqual(status, 404)
        self.assertEqual(problem["code"], "not_found")
        status, _, problem = self.call("POST", "/api/v1/roles", {"name": "attempted"}, token=operator_token, key="role-deny")
        self.assertEqual(status, 403)
        self.assertEqual(problem["code"], "forbidden")

        # The denied action is itself an audit record, while its content is not leaked.
        status, _, audit = self.call("GET", f"/api/v1/audit/events?boxId={first['id']}", token=operator_token)
        self.assertEqual(status, 403)
        self.assertEqual(audit["code"], "forbidden")

    def test_tenant_cannot_mutate_global_policy_or_assign_platform_role(self):
        box = self.create_box("Policy tenant")
        token = f"dev:{box['id']}:{box['ownerIdentityId']}"
        status, _, problem = self.call("POST", "/api/v1/roles", {"name": "tenant-global"}, token=token, key="tenant-role")
        self.assertEqual((status, problem["code"]), (403, "forbidden"))
        status, _, problem = self.call("POST", "/api/v1/permissions", {"code": "tenant-global"}, token=token, key="tenant-permission")
        self.assertEqual((status, problem["code"]), (403, "forbidden"))
        status, _, problem = self.call("POST", "/api/v1/trust-profiles", {"name": "tenant-root", "version": "1", "anchorFingerprints": ["sha256:" + "a" * 64], "hostnames": ["isds.synthetic.test"]}, token=token, key="tenant-trust")
        self.assertEqual((status, problem["code"]), (403, "forbidden"))
        identity_status, _, identity = self.call("POST", f"/api/v1/boxes/{box['id']}/identities", {"subject": "operator"}, token=token, key="tenant-identity")
        self.assertEqual(identity_status, 201)
        status, _, problem = self.call("PUT", f"/api/v1/boxes/{box['id']}/members/{identity['id']}", {"role": "platform-admin"}, token=token, key="tenant-platform-role")
        self.assertEqual((status, problem["code"]), (403, "forbidden"))

    def test_cross_tenant_identity_references_are_rejected(self):
        first = self.create_box("Reference source")
        second = self.create_box("Reference target")
        token = f"dev:{first['id']}:{first['ownerIdentityId']}"
        status, _, problem = self.call("POST", "/api/v1/messages", {"boxId": first["id"], "senderIdentityId": second["ownerIdentityId"], "subject": "must reject"}, token=token, key="cross-tenant-sender")
        self.assertEqual(status, 422)
        self.assertEqual(problem["code"], "cross_tenant_reference")
        status, _, problem = self.call("POST", "/api/v1/auth-methods", {"boxId": first["id"], "identityId": second["ownerIdentityId"], "type": "oidc"}, token=token, key="cross-tenant-auth")
        self.assertEqual(status, 422)
        self.assertEqual(problem["code"], "cross_tenant_reference")

    def test_cursor_pagination_is_bounded_and_stable(self):
        box = self.create_box("Pagination box")
        for number in range(5):
            status, _, _ = self.call("POST", "/api/v1/messages", {"boxId": box["id"], "subject": f"message-{number}"}, key=f"message-{number}")
            self.assertEqual(status, 201)
        status, _, page_one = self.call("GET", f"/api/v1/messages/search?boxId={box['id']}&limit=2")
        self.assertEqual(status, 200)
        self.assertEqual(len(page_one["items"]), 2)
        self.assertIsNotNone(page_one["nextCursor"])
        status, _, page_two = self.call("GET", f"/api/v1/messages/search?boxId={box['id']}&limit=2&cursor={page_one['nextCursor']}")
        self.assertEqual(status, 200)
        self.assertEqual(len(page_two["items"]), 2)
        self.assertTrue({item["id"] for item in page_one["items"]}.isdisjoint({item["id"] for item in page_two["items"]}))
        status, _, problem = self.call("GET", f"/api/v1/messages/search?boxId={box['id']}&limit=101")
        self.assertEqual(status, 400)
        self.assertEqual(problem["code"], "invalid_limit")

    def test_submit_cancel_and_hash_linked_audit(self):
        box = self.create_box("Operations box")
        status, _, message = self.call("POST", "/api/v1/messages", {"boxId": box["id"], "subject": "to submit"}, key="message-submit")
        self.assertEqual(status, 201)
        status, _, operation = self.call("POST", f"/api/v1/messages/{message['id']}/submit", {"targetBoxId": "synthetic-target"}, key="submit")
        self.assertEqual(status, 202)
        status, _, cancelled = self.call("POST", f"/api/v1/operations/{operation['operationId']}/cancel", {}, key="cancel")
        self.assertEqual(status, 202)
        self.assertEqual(cancelled["status"], "cancelled")
        status, _, events = self.call("GET", f"/api/v1/messages/{message['id']}/events")
        self.assertEqual(status, 200)
        self.assertEqual(events["items"][-1]["eventType"], "cancelled")

        status, _, audit = self.call("GET", f"/api/v1/audit/events?boxId={box['id']}&limit=100")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(audit["items"]), 4)
        for previous, current in zip(audit["items"], audit["items"][1:]):
            # API order is newest-first; each older event is linked from the newer event.
            self.assertEqual(previous["previousDigest"], current["eventDigest"])

    def test_problem_json_and_secret_boundary(self):
        status, headers, raw = self.app.handle_request("POST", "/api/v1/boxes", {"Authorization": "Bearer dev:platform"}, {"name": "no-key"})
        problem = json.loads(raw)
        self.assertEqual(status, 400)
        self.assertEqual(headers["content-type"], "application/problem+json")
        self.assertEqual(problem["code"], "idempotency_key_required")
        status, _, problem = self.call("POST", "/api/v1/boxes", {"name": "missing auth"}, token="not-a-token", key="auth-deny")
        self.assertEqual(status, 401)
        self.assertEqual(problem["code"], "invalid_token")

        box = self.create_box("Auth metadata box")
        status, _, problem = self.call("POST", "/api/v1/auth-methods", {"boxId": box["id"], "type": "oidc", "metadata": {"secret": "do-not-store"}}, key="secret-reject")
        self.assertEqual(status, 422)
        self.assertEqual(problem["code"], "secret_not_allowed")


if __name__ == "__main__":
    unittest.main()
