"""Offline deployment CLI contract tests. No live GCP resources or network calls."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "vm" / "deploy.sh"
UPDATE = ROOT / "vm" / "update.sh"
STARTUP = ROOT / "vm" / "startup.sh"


class DeployCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.bin = root / "bin"
        self.bin.mkdir()
        self.marker = root / "events.log"
        (self.bin / "gcloud").write_text("""#!/usr/bin/env bash
set -e
printf 'GCLOUD %s\\n' "$*" >> "$MOCK_MARKER"
case "$*" in
  *'compute instances list'*)
    [[ "${MOCK_LIST_FAIL:-0}" != 1 ]] || { echo 'permission denied' >&2; exit 1; }
    printf '%s\\n' "${MOCK_INSTANCES:-}"
    ;;
  *'compute instances describe'*)
    case "$*" in
      *'get(status)'*) echo RUNNING ;;
      *'get(networkInterfaces'*) echo 203.0.113.15 ;;
    esac ;;
  *'compute firewall-rules describe'*) exit 1 ;;
  *'compute instances create'*) echo 'INSTANCE_CREATED' >> "$MOCK_MARKER" ;;
  *'compute instances start'*) echo 'INSTANCE_STARTED' >> "$MOCK_MARKER" ;;
  *'compute firewall-rules create'*) echo 'FIREWALL_CREATED' >> "$MOCK_MARKER" ;;
  *'config get-value'*) echo mock-gcp-project ;;
esac
""")
        (self.bin / "curl").write_text("""#!/usr/bin/env bash
set -e
printf 'CURL %s\\n' "$*" >> "$MOCK_MARKER"
output=''
while (( $# )); do
  if [[ "$1" == '-o' ]]; then output="$2"; shift 2; else shift; fi
done
if [[ -n "$output" ]]; then
  printf '%s\\n' '#!/usr/bin/env bash' 'echo PROVISION_SCRIPT_CALLED >> "$MOCK_MARKER"' > "$output"
fi
""")
        for name in ("gcloud", "curl"):
            (self.bin / name).chmod(0o755)
        self.env = os.environ.copy()
        self.env["PATH"] = str(self.bin) + os.pathsep + self.env["PATH"]
        self.env["MOCK_MARKER"] = str(self.marker)
        self.env["PROJECT_ID"] = "mock-gcp-project"

    def run_script(self, script, *args):
        return subprocess.run(["bash", str(script), *args], env=self.env,
                              text=True, capture_output=True, timeout=12)

    def events(self):
        return self.marker.read_text() if self.marker.exists() else ""

    def test_shell_syntax_of_all_scripts(self):
        for path in (DEPLOY, UPDATE, STARTUP):
            with self.subTest(script=path.name):
                subprocess.run(["bash", "-n", str(path)], check=True)

    def test_no_existing_vm_calls_provisioner(self):
        result = self.run_script(UPDATE, "--ref", "main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PROVISION_SCRIPT_CALLED", self.events())
        self.assertIn("/main/vm/deploy.sh", self.events())

    def test_no_create_flag_never_provisions(self):
        result = self.run_script(UPDATE, "--no-create", "--ref", "main")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--no-create", result.stderr)
        self.assertNotIn("PROVISION_SCRIPT_CALLED", self.events())

    def test_status_mode_never_provisions(self):
        result = self.run_script(UPDATE, "--status")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot status", result.stderr)
        self.assertNotIn("PROVISION_SCRIPT_CALLED", self.events())

    def test_listing_permission_denied_is_not_absence(self):
        self.env["MOCK_LIST_FAIL"] = "1"
        result = self.run_script(UPDATE, "--ref", "main")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unable to list instances", result.stderr)
        self.assertNotIn("PROVISION_SCRIPT_CALLED", self.events())

    def test_new_provision_creates_one_vm_without_claiming_readiness(self):
        result = self.run_script(DEPLOY, "--ref", "main", "--no-wait")
        self.assertEqual(result.returncode, 0, result.stderr)
        events = self.events()
        self.assertEqual(events.count("INSTANCE_CREATED"), 1)
        self.assertIn("ghost-repo-ref=main", events)
        self.assertIn("FIREWALL_CREATED", events)
        self.assertIn("203.0.113.15.sslip.io", result.stdout)
        self.assertIn("NOT confirmed", result.stderr)
        self.assertNotIn("DEPLOYMENT VERIFIED", result.stdout)

    def test_existing_vm_delegates_to_updater(self):
        self.env["MOCK_INSTANCES"] = "ghost-terminal-ai-vm,us-east1-d,RUNNING"
        result = self.run_script(DEPLOY, "--ref", "main", "--no-wait")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("/main/vm/update.sh", self.events())
        self.assertNotIn("INSTANCE_CREATED", self.events())

    def test_wrong_explicit_zone_is_rejected(self):
        self.env["MOCK_INSTANCES"] = "ghost-terminal-ai-vm,us-east1-d,RUNNING"
        result = self.run_script(UPDATE, "--ref", "main", "--zone", "asia-east1-b")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not asia-east1-b", result.stderr)
        self.assertNotIn("INSTANCE_CREATED", self.events())

    def test_remote_startup_has_version_and_real_health_gates(self):
        source = STARTUP.read_text()
        self.assertIn("ghost-repo-ref", source)
        self.assertIn('git clone --depth=1 --branch="$REPO_REF"', source)
        self.assertIn("HEALTHY=0", source)
        self.assertIn('"ready"', source)
        self.assertNotIn("curl -fsS --max-time 10 http://127.0.0.1:8765/api/health || true", source)


if __name__ == "__main__":
    unittest.main()
