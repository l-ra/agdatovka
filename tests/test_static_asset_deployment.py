import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class StaticAssetDeploymentTest(unittest.TestCase):
    def test_release_image_copies_every_repository_ui_asset(self):
        dockerfile = (ROOT / "deploy/web.Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY ui/ /usr/share/nginx/html/", dockerfile)
        for relative in (
            "ui/index.html", "ui/app.js", "ui/styles.css",
            "ui/user/index.html", "ui/user/app.js", "ui/user/styles.css",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

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

    def test_ui_defaults_use_same_origin_api(self):
        for relative in ("ui/index.html", "ui/user/index.html", "ui/app.js", "ui/user/app.js"):
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("127.0.0.1:8080/api/v1", content, relative)
        self.assertIn('value="/api/v1"', (ROOT / "ui/index.html").read_text(encoding="utf-8"))
        self.assertIn('value="/api/v1"', (ROOT / "ui/user/index.html").read_text(encoding="utf-8"))
        self.assertIn('base: "/api/v1"', (ROOT / "ui/app.js").read_text(encoding="utf-8"))
        self.assertIn('base: "/api/v1"', (ROOT / "ui/user/app.js").read_text(encoding="utf-8"))

    def test_user_ui_authenticates_read_requests(self):
        js = (ROOT / "ui/user/app.js").read_text(encoding="utf-8")
        self.assertIn("headers: { ...headers(false), ...(options.headers || {}) }", js)
        self.assertIn("Authorization: `Bearer ${state.token}`", js)

    def test_nginx_revalidates_html_and_immutably_caches_versioned_assets(self):
        config = (ROOT / "deploy/nginx.conf").read_text(encoding="utf-8")
        self.assertIn("map $host $ui_root", config)
        self.assertIn("/usr/share/nginx/html/user", config)
        self.assertIn('Cache-Control "no-cache, must-revalidate"', config)
        self.assertIn('Cache-Control "public, max-age=31536000, immutable"', config)
        self.assertIn("location /api/", config)


if __name__ == "__main__":
    unittest.main()
