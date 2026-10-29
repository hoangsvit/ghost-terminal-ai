#!/usr/bin/env python3
"""Local-only web server for Ghost Terminal AI. Zero third-party Python packages."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from ghost_terminal.core import MODES, prepare_input
from ghost_terminal.ollama_client import ModelUnavailable, generate_story, model_status

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
ROUTES = {"/": ("index.html", "text/html; charset=utf-8"), "/styles.css": ("styles.css", "text/css; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8")}
MAX_REQUEST_BYTES = 25_000


class GhostHandler(BaseHTTPRequestHandler):
    server_version = "GhostTerminal/1.0"

    def _headers(self, status: int, ctype: str, length: int | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'")
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.end_headers()

    def _json(self, status: int, value: dict) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/health":
            return self._json(200, model_status())
        route = ROUTES.get(path)
        if route is None:
            return self._json(404, {"error": "Not found"})
        file, ctype = route
        content = (PUBLIC / file).read_bytes()
        self._headers(200, ctype, len(content))
        self.wfile.write(content)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/interpret":
            return self._json(404, {"error": "Not found"})
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
            return self._json(403, {"error": "Cross-origin requests are not allowed."})
        if "application/json" not in self.headers.get("Content-Type", ""):
            return self._json(415, {"error": "Expected JSON."})
        length_header = self.headers.get("Content-Length", "")
        if not length_header.isdecimal():
            return self._json(400, {"error": "Content-Length required."})
        length = int(length_header)
        if length > MAX_REQUEST_BYTES:
            return self._json(413, {"error": "Request too large."})
        try:
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                return self._json(400, {"error": "Invalid request object."})
            mode = payload.get("mode", "haunting")
            if mode not in MODES:
                return self._json(400, {"error": "Invalid story mode."})
            clean_log, redactions = prepare_input(payload.get("log"))
        except (ValueError, UnicodeDecodeError, TypeError) as exc:
            return self._json(400, {"error": str(exc) if isinstance(exc, ValueError) else "Invalid JSON."})
        try:
            story = generate_story(clean_log, mode)
        except ModelUnavailable as exc:
            return self._json(503, {"error": str(exc)})
        except Exception:
            self.log_error("Unexpected inference failure")
            return self._json(500, {"error": "Unexpected local inference error."})
        self._json(200, {"story": story, "redactions": redactions, "mode": mode, "model": model_status()["model"]})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    port = int(os.environ.get("GHOST_PORT", "8765"))
    with ThreadingHTTPServer(("127.0.0.1", port), GhostHandler) as server:
        print(f"\n  Ghost Terminal AI | http://127.0.0.1:{port}")
        print("  Local-only • Ollama + Gemma 3 • Ctrl+C to stop\n", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n  Session ended.")


if __name__ == "__main__":
    main()
