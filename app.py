#!/usr/bin/env python3
"""Local-only web server for Ghost Terminal AI. Zero third-party Python packages."""
from __future__ import annotations

import json
import os
from collections import deque
from threading import Lock
from time import monotonic
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from ghost_terminal.core import MODES, prepare_input
from ghost_terminal.ollama_client import ModelUnavailable, generate_story, model_status

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
ROUTES = {"/": ("index.html", "text/html; charset=utf-8"), "/styles.css": ("styles.css", "text/css; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8")}
MAX_REQUEST_BYTES = 25_000
_rate_times = deque()
_rate_lock = Lock()

def _allow_inference() -> bool:
    limit = int(os.environ.get("GHOST_RATE_LIMIT_PER_MINUTE", "0"))
    if limit <= 0:
        return True
    now = monotonic()
    with _rate_lock:
        while _rate_times and _rate_times[0] <= now - 60:
            _rate_times.popleft()
        if len(_rate_times) >= limit:
            return False
        _rate_times.append(now)
        return True

_VM_COPY = {
    "100% LOCAL": "HOSTED ON VM",
    "NO CLOUD API": "NO AI API KEY",
    "AN EXPERIMENT IN LOCAL AI &amp; DIGITAL MEMORY": "AN EXPERIMENT IN OPEN AI &amp; DIGITAL MEMORY",
    "a local AI": "an open-weight AI",
    "Input is redacted locally before inference. Everything stays on your machine; no logs are saved.":
        "Hosted demo: input is processed on Google Compute Engine. Never paste sensitive logs.",
    "LOCALLY GENERATED · NEVER UPLOADED": "GOOGLE CLOUD VM · DO NOT PASTE SECRETS",
    "No account. No API key. No tracking. Just a model running on your machine and the stories your terminal forgot.":
        "No AI API key required. Gemma 3 is hosted on Google Compute Engine; logs travel to the server.",
}

def _render_html(raw: bytes) -> bytes:
    if os.environ.get("GHOST_DEPLOYMENT") != "vm":
        return raw
    html = raw.decode("utf-8")
    for old, new in _VM_COPY.items():
        if old not in html:
            raise ValueError("Hosted mode disclosure template missing")
        html = html.replace(old, new)
    return html.encode("utf-8")



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
            status = model_status()
            status["deployment"] = os.environ.get("GHOST_DEPLOYMENT", "local")
            return self._json(200, status)
        route = ROUTES.get(path)
        if route is None:
            return self._json(404, {"error": "Not found"})
        file, ctype = route
        content = (PUBLIC / file).read_bytes()
        if path == "/":
            content = _render_html(content)
        self._headers(200, ctype, len(content))
        self.wfile.write(content)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/interpret":
            return self._json(404, {"error": "Not found"})
        origin = self.headers.get("Origin")
        if origin:
            allowed = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
            if os.environ.get("GHOST_DEPLOYMENT") == "vm":
                host = self.headers.get("Host", "")
                if host:
                    allowed.add(f"https://{host}")
            if origin not in allowed:
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
        if not _allow_inference():
            return self._json(429, {"error": "Demo is busy. Please retry in about a minute."})
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
