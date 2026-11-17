import importlib.util
import json
from pathlib import Path
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_site", ROOT / "scripts/check_site.py")
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class SiteCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        (self.directory / "icon.png").write_bytes(b"fixture")
        self.html = (
            '<html lang="zh-Hant"><head><link rel="icon" href="/icon.png"></head>'
            '<body><h1>首頁</h1><img src="/icon.png" width="60" height="60" alt="">'
            '<a href="https://example.invalid/">External link</a></body></html>'
        )

    def check(self, html=None):
        (self.directory / "index.html").write_text(self.html if html is None else html)
        CHECKER.check_site(self.directory)

    def test_valid_page(self):
        self.check()

    def test_wrong_language(self):
        with self.assertRaisesRegex(ValueError, "lang=zh-Hant"):
            self.check(self.html.replace("zh-Hant", "en-us"))

    def test_empty_heading(self):
        with self.assertRaisesRegex(ValueError, "empty heading"):
            self.check(self.html.replace("首頁", ""))

    def test_duplicate_h1(self):
        with self.assertRaisesRegex(ValueError, "exactly one h1"):
            self.check(self.html.replace("</body>", "<h1>Another</h1></body>"))

    def test_missing_resource(self):
        with self.assertRaisesRegex(ValueError, "missing local resource"):
            self.check(self.html.replace('src="/icon.png"', 'src="/missing.webp"'))

    def test_missing_srcset_resource(self):
        with self.assertRaisesRegex(ValueError, "missing local resource"):
            self.check(self.html.replace("<img ", '<img srcset="/missing.webp 480w" '))

    def test_missing_dimensions(self):
        with self.assertRaisesRegex(ValueError, "image needs"):
            self.check(self.html.replace('height="60"', ""))

    def test_bad_favicon(self):
        with self.assertRaisesRegex(ValueError, "favicon must reference an image"):
            self.check(self.html.replace('href="/icon.png"', 'href="/"'))

    def test_missing_favicon(self):
        with self.assertRaisesRegex(ValueError, "missing favicon"):
            self.check(self.html.replace('<link rel="icon" href="/icon.png">', ""))

    def test_valid_skip_link(self):
        self.check(self.html.replace("<body>", '<body><a href="#main-content">Skip</a><main id="main-content"></main>'))

    def test_missing_fragment_target(self):
        with self.assertRaisesRegex(ValueError, "missing fragment target"):
            self.check(self.html.replace("<body>", '<body><a href="#missing">Skip</a>'))

    def test_empty_output_directory(self):
        with self.assertRaisesRegex(ValueError, "no generated HTML"):
            CHECKER.check_site(self.directory)


class DependencyTests(unittest.TestCase):
    def test_locked_dependencies(self):
        package = json.loads((ROOT / "package.json").read_text())
        lock = json.loads((ROOT / "package-lock.json").read_text())
        for group in ("dependencies", "devDependencies"):
            for name, version in package[group].items():
                with self.subTest(dependency=name):
                    self.assertEqual(lock["packages"][f"node_modules/{name}"]["version"], version)
        self.assertNotIn("jquery", package["dependencies"])
        self.assertTrue(all(p.get("integrity") for name, p in lock["packages"].items() if name))

    def test_project_owned_sass(self):
        for path in (ROOT / "assets/scss").glob("*.scss"):
            with self.subTest(path=path.name):
                self.assertNotIn("@import", path.read_text())
                self.assertNotIn("darken(", path.read_text())

    def test_theme_independent_configuration(self):
        config = tomllib.loads((ROOT / "config.toml").read_text())
        self.assertNotIn("theme", config)
        self.assertEqual(config["locale"], "zh-Hant")
        self.assertNotIn("jQuery", (ROOT / "layouts/partials/script.html").read_text())
        self.assertNotIn("googleapis.com", (ROOT / "layouts/partials/style.html").read_text())


if __name__ == "__main__":
    unittest.main()
