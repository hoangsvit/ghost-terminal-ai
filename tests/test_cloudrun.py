"""Cloud Run specific behavior, all tested offline (no GCP account required)."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from app import _allow_inference, _public_html, _rate_events
from ghost_terminal.ollama_client import generate_story

WEB_HTML = (Path(__file__).resolve().parents[1] / "public" / "index.html").read_bytes()


class CloudRunTests(unittest.TestCase):
    def test_original_local_copy_remains_unchanged(self):
        with patch.dict("os.environ", {"GHOST_DEPLOYMENT": "local"}):
            self.assertEqual(_public_html(WEB_HTML), WEB_HTML)

    def test_cloud_html_explains_remote_processing(self):
        with patch.dict("os.environ", {"GHOST_DEPLOYMENT": "cloudrun"}):
            page = _public_html(WEB_HTML).decode("utf-8")
        self.assertIn("GOOGLE CLOUD RUN", page)
        self.assertIn("input is processed on Google Cloud Run", page)
        self.assertNotIn("100% LOCAL", page)
        self.assertNotIn("Everything stays on your machine", page)
        self.assertNotIn("LOCALLY GENERATED · NEVER UPLOADED", page)

    def test_memory_only_per_instance_rate_limit(self):
        with patch.dict("os.environ", {"GHOST_RATE_LIMIT_PER_MINUTE": "2"}):
            _rate_events.clear()
            with patch("app.monotonic", side_effect=[100.0, 101.0, 102.0, 161.0]):
                self.assertTrue(_allow_inference())
                self.assertTrue(_allow_inference())
                self.assertFalse(_allow_inference())
                self.assertTrue(_allow_inference())
        _rate_events.clear()

    def test_local_mode_has_no_rate_limit(self):
        with patch.dict("os.environ", {"GHOST_RATE_LIMIT_PER_MINUTE": "0"}):
            self.assertTrue(_allow_inference())

    def test_cloud_inference_timeout_is_configurable(self):
        result = {
            "title": "The Last Light",
            "transmission": "The server came back at midnight.",
            "whisper": "I remember.",
            "echoes": [],
        }
        with patch.dict("os.environ", {"GHOST_INFERENCE_TIMEOUT": "240"}):
            with patch("ghost_terminal.ollama_client._request", return_value={"response": json.dumps(result)}) as call:
                generated = generate_story("git status", "haunting")
        self.assertEqual(generated["title"], "The Last Light")
        self.assertEqual(call.call_args.kwargs["timeout"], 240)


if __name__ == "__main__":
    unittest.main()
