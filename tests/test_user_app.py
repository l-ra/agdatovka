import base64
import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

from ag_datovka import create_app

ROOT = Path(__file__).parents[1]


class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.controls = []; self.labels = set()
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"input", "select", "textarea"} and values.get("id"): self.controls.append(values["id"])
        if tag == "label" and values.get("for"): self.labels.add(values["for"])


class UserAppTest(unittest.TestCase):
    def setUp(self): self.app = create_app(":memory:"); self.number = 0
    def tearDown(self): self.app.close()
    def call(self, method, path, body=None, token="dev:platform"):
        self.number += 1
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if method in {"POST", "PATCH", "PUT", "DELETE"}: headers["Idempotency-Key"] = f"user-test-{self.number}"
        status, _, raw = self.app.handle_request(method, path, headers, body or {})
        return status, json.loads(raw)

    def test_additive_session_read_and_download_contract(self):
        status, box = self.call("POST", "/api/v1/boxes", {"name": "User box", "kind": "test"})
        self.assertEqual(status, 201)
        status, identity = self.call("POST", f"/api/v1/boxes/{box['id']}/identities", {"subject": "user-1", "displayName": "User"})
        self.assertEqual(status, 201)
        status, _ = self.call("PUT", f"/api/v1/boxes/{box['id']}/members/{identity['id']}", {"role": "box-operator"})
        self.assertEqual(status, 200)
        token = f"dev:{box['id']}:{identity['id']}"
        status, session = self.call("GET", "/api/v1/session", token=token)
        self.assertEqual((status, session["tenant"], session["identity"]["id"]), (200, box["id"], identity["id"]))
        status, message = self.call("POST", "/api/v1/messages", {"boxId": box["id"], "subject": "Hello", "senderIdentityId": identity["id"]}, token=token)
        self.assertEqual(status, 201)
        payload = base64.b64encode(b"hello").decode()
        status, attachment = self.call("POST", f"/api/v1/messages/{message['id']}/attachments", {"filename": "hello.txt", "mediaType": "text/plain", "contentBase64": payload, "byteLength": 5}, token=token)
        self.assertEqual((status, attachment["verified"]), (201, True))
        status, read = self.call("PATCH", f"/api/v1/messages/{message['id']}/read", {"read": True}, token=token)
        self.assertEqual((status, read["read"]), (200, True))
        status, detail = self.call("GET", f"/api/v1/messages/{message['id']}", token=token)
        self.assertEqual((status, detail["readAt"] is not None), (200, True))
        status, downloaded = self.call("GET", f"/api/v1/messages/{message['id']}/attachments/{attachment['id']}", token=token)
        self.assertEqual((status, downloaded["contentBase64"]), (200, payload))

    def test_user_ui_is_separate_and_labelled(self):
        html = (ROOT / "ui/user/index.html").read_text(encoding="utf-8")
        js = (ROOT / "ui/user/app.js").read_text(encoding="utf-8")
        parser = Parser(); parser.feed(html)
        self.assertTrue(set(parser.controls) <= parser.labels)
        for marker in ("/session", "/messages", "/attachments", "/read", "/events", "/exports", "Idempotency-Key", "sessionStorage"):
            self.assertIn(marker, js)
        self.assertIn("separate from the management console", html)


if __name__ == "__main__": unittest.main()
