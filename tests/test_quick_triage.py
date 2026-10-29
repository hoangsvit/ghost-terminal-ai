"""Offline acceptance and security tests for instant triage and timestamp-aware diffs."""
from __future__ import annotations

import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from app import GhostHandler
from ghost_terminal.analysis import compare_logs, quick_triage


class TimestampCompareTests(unittest.TestCase):
    def test_default_diff_retains_timestamp_changes(self):
        diff = compare_logs("[12:00:01] Ready", "[12:01:01] Ready")
        self.assertEqual(diff["added_count"], 1)
        self.assertEqual(diff["removed_count"], 1)
        self.assertFalse(diff["ignore_timestamps"])

    def test_opt_in_ignores_clock_only(self):
        diff = compare_logs("[12:00:01] Ready", "[12:01:01] Ready", ignore_timestamps=True)
        self.assertEqual(diff["added_count"], 0)
        self.assertEqual(diff["removed_count"], 0)
        self.assertTrue(diff["ignore_timestamps"])

    def test_iso_datetime_prefix(self):
        before = "2026-10-29T09:12:12.123Z Service ready"
        after = "2026-10-29T09:17:00.456Z Service ready"
        diff = compare_logs(before, after, ignore_timestamps=True)
        self.assertEqual(diff["added_count"], 0)

    def test_timestamped_content_changes_still_count(self):
        before = "[12:00:01] Success"
        after = "[12:01:01] ERROR: EADDRINUSE"
        diff = compare_logs(before, after, ignore_timestamps=True)
        self.assertEqual(diff["added_count"], 1)
        self.assertEqual(diff["removed_count"], 1)
        self.assertEqual(diff["added"][0]["line"], 1)
        self.assertEqual(diff["added"][0]["text"], after)
        self.assertEqual(diff["new_error_signals"][0]["type"], "network")

    def test_does_not_strip_times_in_message_body(self):
        before = "Ready at 12:00:01"
        after = "Ready at 12:01:01"
        diff = compare_logs(before, after, ignore_timestamps=True)
        self.assertEqual(diff["added_count"], 1)

    def test_match_remains_line_numbered(self):
        before = "[12:00:01] Starting\n[12:00:02] Running"
        after = "[12:04:01] Starting\n[12:04:02] ERROR: EADDRINUSE"
        diff = compare_logs(before, after, ignore_timestamps=True)
        self.assertEqual(diff["added_count"], 1)
        self.assertEqual(diff["new_error_signals"][0]["line"], 2)


class InstantRulesTests(unittest.TestCase):
    def test_known_port_conflict(self):
        result = quick_triage("Starting\nERROR: EADDRINUSE")
        self.assertEqual(result["engine"], "rules")
        self.assertEqual(result["signals"]["severity"], "high")
        self.assertEqual(result["analysis"]["confidence"], "rule-based")
        self.assertIn("line 2", result["analysis"]["summary"])
        self.assertGreaterEqual(len(result["analysis"]["checks"]), 2)

    def test_no_known_error_stays_uncertain(self):
        result = quick_triage("Worker started\nReady")
        self.assertEqual(result["signals"]["severity"], "info")
        self.assertIn("cannot be inferred", result["analysis"]["probable_cause"])
        self.assertIn("not prove", result["analysis"]["probable_cause"])

    def test_new_error_signal_takes_priority(self):
        baseline = "ERROR: ENOSPC\nReady"
        current = "ERROR: ENOSPC\nERROR: EADDRINUSE"
        result = quick_triage(current, baseline=baseline)
        self.assertIn("line 2", result["analysis"]["summary"])
        self.assertEqual(result["diff"]["new_error_signals"][0]["type"], "network")

    def test_compare_identical_after_normalization(self):
        result = quick_triage("[12:03:01] Healthy", baseline="[12:01:01] Healthy",
                              ignore_timestamps=True)
        self.assertEqual(result["diff"]["added_count"], 0)
        self.assertIn("No meaningful differences", result["analysis"]["summary"])


class HttpQuickScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), GhostHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=4)

    def post(self, path, payload, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=4)
        conn.request("POST", path, body=json.dumps(payload), headers=headers or {
            "Content-Type": "application/json"})
        res = conn.getresponse()
        status = res.status
        data = json.loads(res.read())
        conn.close()
        return status, data

    def test_inspect_without_ollama_or_inference_quota(self):
        with patch("app.generate_diagnosis", side_effect=AssertionError("AI was called")), \
             patch("app._allow_inference", side_effect=AssertionError("quota checked")), \
             patch("app.model_status", side_effect=AssertionError("health queried")):
            status, result = self.post("/api/inspect", {"log": "ERROR: EADDRINUSE"})
        self.assertEqual(status, 200)
        self.assertEqual(result["engine"], "rules")
        self.assertEqual(result["signals"]["evidence"][0]["line"], 1)

    def test_inspect_compare_returns_diff(self):
        status, data = self.post("/api/inspect", {
            "baseline": "[11:00:00] Ready", "log": "[12:00:00] Ready",
            "ignore_timestamps": True})
        self.assertEqual(status, 200)
        self.assertEqual(data["mode"], "compare")
        self.assertEqual(data["diff"]["added_count"], 0)

    def test_inspect_secret_redaction(self):
        status, data = self.post("/api/inspect", {"log": "password=example-password\nERROR: EADDRINUSE"})
        self.assertEqual(status, 200)
        self.assertEqual(data["redactions"], 1)
        self.assertNotIn("example-password", json.dumps(data))

    def test_reject_non_boolean_ignore_flag(self):
        status, body = self.post("/api/inspect", {"log": "ERROR", "ignore_timestamps": "false"})
        self.assertEqual(status, 400)
        self.assertIn("boolean", body["error"])

    def test_reject_missing_baseline_if_provided(self):
        status, body = self.post("/api/inspect", {"log": "ERROR", "baseline": ""})
        self.assertEqual(status, 400)

    def test_reject_untrusted_origin(self):
        status, _ = self.post("/api/inspect", {"log": "ERROR"}, headers={
            "Content-Type": "application/json",
            "Origin": "https://malicious.example"})
        self.assertEqual(status, 403)

    def test_inspect_html_assets_served(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        conn.request("GET", "/")
        res = conn.getresponse()
        html = res.read()
        conn.close()
        self.assertEqual(res.status, 200)
        self.assertIn(b'id="quick-scan-btn"', html)
        self.assertIn(b'id="download-report-btn"', html)
        self.assertIn(b'id="ignore-timestamps"', html)


if __name__ == "__main__":
    unittest.main()
