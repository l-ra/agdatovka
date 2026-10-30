import json
import unittest
from pathlib import Path

from qa.performance_readiness import validate
from qa.scans import scan_fixture_text


ROOT = Path(__file__).parents[1]


class PerformanceReadinessTest(unittest.TestCase):
    def test_manifest_validates_without_execution(self):
        self.assertEqual(validate(), [])

    def test_harness_is_validation_only(self):
        harness = json.loads((ROOT / "qa" / "performance-harness.json").read_text())
        self.assertFalse(harness["loadExecution"])
        self.assertIn("--validate", harness["command"])

    def test_readiness_artifacts_have_no_production_or_secret_findings(self):
        paths = [
            ROOT / "qa" / "performance-scenarios.json",
            ROOT / "qa" / "performance-harness.json",
            ROOT / "evidence" / "AGDA-13" / "README.md",
            ROOT / "evidence" / "AGDA-13" / "acceptance-record.json",
        ]
        self.assertEqual(scan_fixture_text([path.read_text(encoding="utf-8") for path in paths]), [])

    def test_scenarios_cover_required_families(self):
        manifest = json.loads((ROOT / "qa" / "performance-scenarios.json").read_text())
        names = {item["name"] for item in manifest["scenarios"]}
        for expected in ("sustained-admission", "large-and-resumable-content", "idempotency-replay", "worker-failure-recovery", "upstream-and-store-faults", "horizontal-scale-and-partitions", "retention-and-evidence-workload", "full-recovery-and-cleanup"):
            self.assertIn(expected, names)
        self.assertEqual(manifest["target"]["acceptedMessagesPerMinute"], 1000)


if __name__ == "__main__":
    unittest.main()
