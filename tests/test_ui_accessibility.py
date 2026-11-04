import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parents[1]


class UiParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids = set(); self.controls = []; self.labels = []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values: self.ids.add(values["id"])
        if tag in {"input", "select", "textarea"} and values.get("id"): self.controls.append((tag, values["id"]))
        if tag == "label": self.labels.append(values.get("for"))


class AccessibleManagementUiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "ui/index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "ui/app.js").read_text(encoding="utf-8")
        parser = UiParser(); parser.feed(cls.html); cls.parser = parser

    def test_all_form_controls_have_real_labels_and_unique_ids(self):
        self.assertEqual(len(self.parser.ids), len(re.findall(r'\bid="([^"]+)"', self.html)))
        labelled = set(self.parser.labels)
        for _tag, control_id in self.parser.controls:
            self.assertIn(control_id, labelled, control_id)

    def test_semantic_regions_and_focusable_error_summary_exist(self):
        for landmark in ('<main>', '<footer>', 'role="status"', 'aria-live="polite"', 'role="alert"', 'tabindex="-1"'):
            self.assertIn(landmark, self.html)
        self.assertIn('error-summary', self.js)
        self.assertIn('.focus()', self.js)

    def test_required_vertical_slice_actions_are_wired(self):
        for endpoint in ('/boxes', '/identities', '/members/', '/messages', '/attachments', '/submit', '/operations/', '/events', '/exports', '/audit/events', '/trust-profiles', '/endpoint-profiles', '/retention/legal-holds', '/retention/deletion-requests', '/retention/restore', '/receipts/'):
            self.assertIn(endpoint, self.js)
        self.assertIn('request("")', self.js)
        self.assertIn('Idempotency-Key', self.js)
        self.assertIn('headers: { ...headers(false), ...(options.headers || {}) }', self.js)
        self.assertIn('fieldErrors', self.js)
        self.assertNotRegex(self.js, r'innerHTML|document\.write')

    def test_fixture_is_synthetic_and_covers_manual_scenario(self):
        fixture = json.loads((ROOT / "fixtures/ui/management-scenario.json").read_text(encoding="utf-8"))
        self.assertTrue(fixture["syntheticOnly"])
        self.assertEqual(fixture["profile"], "ag-synthetic")
        self.assertEqual(fixture["steps"][-1]["result"], "manual-review")


if __name__ == "__main__":
    unittest.main()
