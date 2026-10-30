import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("fork_smoke", ROOT / "fork/scripts/smoke.py")
assert SPEC and SPEC.loader
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


class ForkSmokeTests(unittest.TestCase):
    def test_offline_fixture_is_deterministic(self):
        profile = smoke.preflight("offline-fixture")
        self.assertEqual(profile["mode"], "offline")
        self.assertEqual(smoke.offline_smoke(), ["parse", "receipt", "search", "export"])

    def test_network_profiles_keep_placeholders(self):
        for name in ("ag-synthetic", "isds-public-test"):
            self.assertIn(".invalid", smoke.preflight(name)["endpoint"])

    def test_production_host_is_rejected(self):
        path = smoke.PROFILES / "ag-synthetic.yaml"
        original = path.read_text(encoding="utf-8")
        try:
            path.write_text(original.replace("AG_SYNTHETIC_HOST.invalid", "datovka.gov.cz"), encoding="utf-8")
            with self.assertRaises(ValueError):
                smoke.preflight("ag-synthetic")
        finally:
            path.write_text(original, encoding="utf-8")

    def test_inline_secret_is_rejected(self):
        path = smoke.PROFILES / "offline-fixture.yaml"
        original = path.read_text(encoding="utf-8")
        try:
            path.write_text(original + "\npassword: never-inline\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                smoke.preflight("offline-fixture")
        finally:
            path.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
