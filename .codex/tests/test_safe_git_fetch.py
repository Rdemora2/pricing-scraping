import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "safe_git_fetch.py"
SPEC = importlib.util.spec_from_file_location("safe_git_fetch", MODULE_PATH)
safe_git_fetch = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(safe_git_fetch)


class SafeGitFetchTests(unittest.TestCase):
    def test_environment_drops_credentials(self):
        clean = safe_git_fetch.sanitized_environment({"PATH": "/bin", "GH_TOKEN": "x", "SSH_AUTH_SOCK": "x"})
        self.assertEqual(clean["PATH"], "/bin")
        self.assertNotIn("GH_TOKEN", clean)
        self.assertNotIn("SSH_AUTH_SOCK", clean)
        self.assertEqual(clean["GIT_TERMINAL_PROMPT"], "0")

    def test_cli_is_closed(self):
        self.assertEqual(safe_git_fetch.main(["self-test"]), 0)
        self.assertEqual(safe_git_fetch.main(["unknown"]), 2)
        self.assertEqual(safe_git_fetch.main(["--status", "extra"]), 2)


if __name__ == "__main__":
    unittest.main()
