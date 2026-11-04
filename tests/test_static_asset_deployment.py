import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class StaticAssetDeploymentTest(unittest.TestCase):
    def test_web_image_packages_both_static_apps_and_derives_asset_version(self):
        dockerfile = (ROOT / "deploy/web.Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY ui/ /usr/share/nginx/html/", dockerfile)
        self.assertIn("sha256sum", dockerfile)
        self.assertIn("__AGDA_ASSET_VERSION__", dockerfile)
        self.assertIn("/usr/share/nginx/html/user/index.html", dockerfile)

    def test_compose_builds_web_image_from_repository_sources(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("dockerfile: deploy/web.Dockerfile", compose)
        self.assertNotIn("image: nginx:1.27-alpine", compose)
        self.assertNotIn("./deploy/nginx.conf:/etc/nginx/conf.d/default.conf:ro", compose)

    def test_html_references_are_versioned(self):
        for relative in ("ui/index.html", "ui/user/index.html"):
            html = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("styles.css?v=__AGDA_ASSET_VERSION__", html)
            self.assertIn("app.js?v=__AGDA_ASSET_VERSION__", html)

    def test_nginx_revalidates_html_and_immutably_caches_versioned_assets(self):
        config = (ROOT / "deploy/nginx.conf").read_text(encoding="utf-8")
        self.assertIn("map $host $ui_root", config)
        self.assertIn("/usr/share/nginx/html/user", config)
        self.assertIn('Cache-Control "no-cache, must-revalidate"', config)
        self.assertIn('Cache-Control "public, max-age=31536000, immutable"', config)
        self.assertIn("location /api/", config)


if __name__ == "__main__":
    unittest.main()
