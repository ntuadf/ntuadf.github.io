import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/CloudflarePurgeCache.sh"


class CachePurgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        directory = Path(self.temp.name)
        self.arguments = directory / "arguments.json"
        curl = directory / "curl"
        curl.write_text(
            "#!/usr/bin/python3\n"
            "import json, os, sys\n"
            "with open(os.environ['MOCK_ARGUMENTS'], 'w') as output:\n"
            "    json.dump(sys.argv[1:], output)\n"
            "if os.environ.get('MOCK_CURL_ERROR'):\n"
            "    sys.exit(int(os.environ['MOCK_CURL_ERROR']))\n"
            "print(os.environ['MOCK_BODY'] + 'HTTP_STATUS:' + os.environ['MOCK_STATUS'], end='')\n"
        )
        curl.chmod(0o700)
        self.env = {
            "PATH": f"{directory}:/usr/bin:/bin",
            "CLOUDFLARE_TOKEN": "dummy-token",
            "CLOUDFLARE_ZONE": "dummy-zone",
            "MOCK_ARGUMENTS": str(self.arguments),
            "MOCK_BODY": '{"success":true}',
            "MOCK_STATUS": "200",
        }

    def run_purge(self, **overrides):
        return subprocess.run(
            ["bash", str(SCRIPT)],
            env={**self.env, **overrides},
            capture_output=True,
            text=True,
            timeout=5,
        )

    def test_success_and_timeouts(self):
        result = self.run_purge()
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(self.arguments.read_text())
        self.assertIn("Authorization: Bearer dummy-token", args)
        self.assertIn("--connect-timeout", args)
        self.assertIn("--max-time", args)
        self.assertEqual(json.loads(args[args.index("--data") + 1]), {"purge_everything": True})

    def test_api_failure_with_http_200(self):
        result = self.run_purge(MOCK_BODY='{"success":false,"errors":[{"message":"rejected"}]}')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rejected", result.stderr)

    def test_http_error_even_with_success_body(self):
        self.assertNotEqual(self.run_purge(MOCK_STATUS="403").returncode, 0)

    def test_invalid_response(self):
        for body in ("not json", "[]", "{}", '{"success":"true"}'):
            with self.subTest(body=body):
                self.assertNotEqual(self.run_purge(MOCK_BODY=body).returncode, 0)

    def test_network_failure(self):
        self.assertNotEqual(self.run_purge(MOCK_CURL_ERROR="28").returncode, 0)

    def test_missing_credentials(self):
        result = self.run_purge(CLOUDFLARE_TOKEN="")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.arguments.exists())

    def test_missing_zone(self):
        self.assertNotEqual(self.run_purge(CLOUDFLARE_ZONE="").returncode, 0)
        self.assertFalse(self.arguments.exists())

    def test_legacy_key_requires_email(self):
        self.assertNotEqual(self.run_purge(CLOUDFLARE_KEY="dummy-key").returncode, 0)
        self.assertFalse(self.arguments.exists())

    def test_legacy_key(self):
        result = self.run_purge(CLOUDFLARE_KEY="dummy-key", CLOUDFLARE_EMAIL="test@example.invalid")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(self.arguments.read_text())
        self.assertIn("X-Auth-Key: dummy-key", args)
        self.assertIn("X-Auth-Email: test@example.invalid", args)

    def test_specific_urls(self):
        urls = ["https://example.invalid/page?one=1&two=2"]
        result = self.run_purge(PURGE_URLS=json.dumps(urls))
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(self.arguments.read_text())
        self.assertEqual(json.loads(args[args.index("--data") + 1]), {"files": urls})

    def test_invalid_urls_do_not_call_api(self):
        for urls in ("broken json", "{}", "[]", "[1]", '[""]'):
            with self.subTest(urls=urls):
                self.assertNotEqual(self.run_purge(PURGE_URLS=urls).returncode, 0)
                self.assertFalse(self.arguments.exists())


if __name__ == "__main__":
    unittest.main()
