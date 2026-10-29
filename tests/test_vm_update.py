"""VM updater must be safe to parse and useful without gcloud installed."""
from pathlib import Path
import subprocess
import unittest

UPDATER = Path(__file__).resolve().parents[1] / "vm" / "update.sh"


class VmUpdateTests(unittest.TestCase):
    def test_script_syntax(self):
        subprocess.run(["bash", "-n", str(UPDATER)], check=True)

    def test_remote_script_syntax(self):
        source = UPDATER.read_text()
        self.assertIn("<<'REMOTE'\n", source)
        remote = source.split("<<'REMOTE'\n", 1)[1].split("\nREMOTE\n", 1)[0]
        subprocess.run(["bash", "-n"], input=remote, text=True, check=True)

    def test_help_before_any_gcloud_call(self):
        result = subprocess.run(["bash", str(UPDATER), "--help"], capture_output=True,
                                text=True, check=True)
        self.assertIn("--rollback", result.stdout)
        self.assertIn("--ref main", result.stdout)
        self.assertIn("EXISTING", result.stdout.upper())

    def test_bad_branch_rejected_early(self):
        result = subprocess.run(["bash", str(UPDATER), "--ref", "main;rm -rf /"],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid Git branch", result.stderr)

    def test_unknown_option_rejected(self):
        result = subprocess.run(["bash", str(UPDATER), "--does-not-exist"],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown option", result.stderr)

    def test_never_recreates_vm_or_downloads_model(self):
        source = UPDATER.read_text()
        self.assertNotIn("compute instances create", source)
        self.assertNotIn("ollama pull", source)
        self.assertNotIn("systemctl restart ollama", source)
        self.assertIn("flock -n", source)
        self.assertIn("gitapp status --porcelain", source)
        self.assertIn("trap recover ERR", source)
        self.assertIn("gitapp update-ref refs/ghost-terminal/previous", source)


if __name__ == "__main__":
    unittest.main()
