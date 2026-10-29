"""A deliberately local-only Ollama transport (no cloud fallback)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from .core import STORY_SCHEMA, build_prompt, validate_story

DEFAULT_URL = "http://127.0.0.1:11434"


class ModelUnavailable(Exception):
    """The requested local model cannot be reached or used."""


def base_url() -> str:
    raw = os.environ.get("GHOST_OLLAMA_URL", DEFAULT_URL).rstrip("/")
    parts = urlsplit(raw)
    if parts.scheme != "http" or parts.hostname not in ("localhost", "127.0.0.1", "::1") or parts.username or parts.password or parts.path or parts.query or parts.fragment:
        raise ValueError("GHOST_OLLAMA_URL must be a local HTTP Ollama host.")
    return raw


def model_name() -> str:
    return os.environ.get("GHOST_MODEL", "gemma3:1b").strip() or "gemma3:1b"


def _request(path: str, payload: dict | None = None, timeout: int = 5) -> dict:
    try:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            base_url() + path,
            data=body,
            headers={"Content-Type": "application/json"} if body is not None else {},
            method="POST" if body is not None else "GET",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.load(response)
            if not isinstance(result, dict):
                raise ModelUnavailable("Ollama returned an unexpected response.")
            return result
    except urllib.error.HTTPError as exc:
        raise ModelUnavailable(f"Ollama rejected the request (HTTP {exc.code}). Check the model name.") from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise ModelUnavailable("Local Ollama is unavailable or timed out. Start Ollama and check the model.") from exc


def model_status() -> dict:
    model = model_name()
    try:
        response = _request("/api/tags", timeout=2)
        tags = [x.get("name", "") for x in response.get("models", []) if isinstance(x, dict)]
        present = model in tags or (":" not in model and any(x.startswith(model + ":") for x in tags))
        return {"ready": present, "connected": True, "model": model, "message": "Model ready" if present else f"Model not found: run ollama pull {model}"}
    except (ValueError, ModelUnavailable):
        return {"ready": False, "connected": False, "model": model, "message": "Ollama offline — start Ollama locally"}


def generate_story(log: str, mode: str) -> dict:
    system, prompt = build_prompt(log, mode)
    payload = {
        "model": model_name(),
        "system": system,
        "prompt": prompt,
        "stream": False,
        "format": STORY_SCHEMA,
        "options": {"temperature": 0.75, "num_predict": 550},
        "keep_alive": "5m",
    }
    answer = _request("/api/generate", payload, timeout=110)
    try:
        story = json.loads(answer["response"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ModelUnavailable("Model did not return valid JSON. Try generating again.") from exc
    try:
        return validate_story(story, log)
    except ValueError as exc:
        raise ModelUnavailable("Model response was incomplete. Try again.") from exc
