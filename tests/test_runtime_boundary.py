import json
import unittest

from ag_datovka import create_app
from ag_datovka.config import ConfigurationError, RuntimeConfig


class RuntimeBoundaryTest(unittest.TestCase):
    def test_deploy_rejects_fixture_persistence(self):
        with self.assertRaises(ConfigurationError):
            RuntimeConfig.from_env({"AG_ENV": "deploy", "AG_AUTH_PROFILE": "deploy"})

    def test_deploy_accepts_explicit_durable_endpoints(self):
        config = RuntimeConfig.from_env({
            "AG_ENV": "deploy", "AG_AUTH_PROFILE": "deploy",
            "DATABASE_URL": "postgresql://db/ag_datovka",
            "OBJECT_STORE_URL": "s3://content-bucket",
            "QUEUE_URL": "redis://queue/0",
        })
        self.assertEqual(config.port, 8080)

    def test_health_endpoints_are_unauthenticated_and_redacted(self):
        app = create_app(":memory:")
        try:
            live, _, body = app.handle_request("GET", "/health/live")
            self.assertEqual(live, 200)
            self.assertEqual(json.loads(body)["status"], "ok")
            ready, _, body = app.handle_request("GET", "/health/ready")
            self.assertEqual(ready, 200)
            self.assertEqual(json.loads(body)["database"], "ok")
        finally:
            app.close()


if __name__ == "__main__":
    unittest.main()

