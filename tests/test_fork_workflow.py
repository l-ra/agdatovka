import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ForkWorkflowTests(unittest.TestCase):
    def test_local_synthetic_workflow_is_redacted_and_complete(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "fork/scripts/local_workflow.py")],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        manifest = json.loads(result.stdout)
        self.assertEqual(manifest["status"], "pass")
        self.assertEqual(manifest["messageStatus"], "delivered")
        self.assertEqual(manifest["receiptStatus"], "delivered")
        self.assertEqual(manifest["searchMatches"], 1)
        self.assertEqual(manifest["exportStatus"], "completed")
        self.assertEqual(manifest["workflow"], ["login/configuration", "send", "retrieve", "lifecycle/receipt", "search", "export"])
        self.assertNotIn("contentBase64", result.stdout)
        self.assertNotIn("dev:", result.stdout)


if __name__ == "__main__":
    unittest.main()
