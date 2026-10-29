"""Offline tests for the optional VM-hosted mode. Does not test a real GCP VM."""
import unittest
from unittest.mock import patch

from app import _allow_inference, _rate_times, _render_html, PUBLIC


class VmTests(unittest.TestCase):
    def test_local_mode_keeps_original_html(self):
        html = (PUBLIC / "index.html").read_bytes()
        with patch.dict("os.environ", {"GHOST_DEPLOYMENT": "local"}):
            self.assertEqual(_render_html(html), html)

    def test_vm_page_discloses_hosted_inference(self):
        html = (PUBLIC / "index.html").read_bytes()
        with patch.dict("os.environ", {"GHOST_DEPLOYMENT": "vm"}):
            content = _render_html(html).decode("utf-8")
        self.assertIn("HOSTED ON VM", content)
        self.assertIn("input is processed on Google Compute Engine", content)
        self.assertNotIn("100% LOCAL", content)
        self.assertNotIn("Everything stays on your machine", content)

    def test_throttle_window(self):
        _rate_times.clear()
        with patch.dict("os.environ", {"GHOST_RATE_LIMIT_PER_MINUTE": "2"}):
            with patch("app.monotonic", side_effect=[100.0, 101.0, 102.0, 161.0]):
                self.assertTrue(_allow_inference())
                self.assertTrue(_allow_inference())
                self.assertFalse(_allow_inference())
                self.assertTrue(_allow_inference())
        _rate_times.clear()

    def test_no_throttle_in_local_mode(self):
        with patch.dict("os.environ", {"GHOST_RATE_LIMIT_PER_MINUTE": "0"}):
            self.assertTrue(_allow_inference())

if __name__ == "__main__":
    unittest.main()
