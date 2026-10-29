"""Deterministic evidence extraction from sanitized logs; no model calls here."""
from __future__ import annotations

from difflib import SequenceMatcher
import re
from typing import Any

# Pre-filter source signals before asking the model for an explanation.
# These are heuristics, NOT confirmed root causes.
RULES = (
    ("resource", "Disk is full", "high", re.compile(r"(?i)\b(?:ENOSPC|no space left on device|disk full)\b")),
    ("memory", "Process ran out of memory", "high", re.compile(r"(?i)\b(?:OOMKilled|out of memory|JavaScript heap out of memory|exit(?:ed)? (?:code |status )?137)\b")),
    ("network", "Address/port conflict", "high", re.compile(r"(?i)\b(?:EADDRINUSE|address already in use|bind: address already in use)\b")),
    ("permission", "Permission denied", "medium", re.compile(r"(?i)\b(?:EACCES|EPERM|permission denied|access denied)\b")),
    ("authentication", "Authentication or access rejected", "medium", re.compile(r"(?i)\b(?:unauthorized|invalid token|authentication failed|forbidden|HTTP 401|HTTP 403)\b")),
    ("dependency", "Missing package or dependency", "medium", re.compile(r"(?i)(?:ModuleNotFoundError|Cannot find module|No module named|package .* not found|npm ERR! code ERESOLVE)")),
    ("deployment", "Deployment location restricted", "medium", re.compile(r"(?i)(?:constraints/gcp\.resourceLocations|location .*violat.*constraint|FAILED_PRECONDITION)")),
    ("network", "Connection failed or timed out", "medium", re.compile(r"(?i)\b(?:ECONNREFUSED|ETIMEDOUT|connection refused|connection timed out|timeout exceeded)\b")),
    ("runtime", "Unhandled runtime error", "medium", re.compile(r"(?i)(?:Traceback \(most recent call last\)|\b(?:TypeError|ValueError|ReferenceError|SyntaxError):)")),
    ("build", "Build or command failed", "medium", re.compile(r"(?i)(?:\bBUILD FAILED\b|\bnpm ERR!\b|error: failed to|failed to build|error during build|process exited with code [1-9])")),
    ("http", "Server returned an error", "medium", re.compile(r"(?i)(?:HTTP[/ ](?:500|502|503|504)\b|status(?: code)?[:= ]+(?:500|502|503|504)\b)")),
    ("generic", "Error reported", "low", re.compile(r"(?i)(?:^|\s)(?:ERROR|FATAL|PANIC)(?::|\s|$)")),
)


def extract_evidence(log: str, limit: int = 8) -> dict[str, Any]:
    """Return real numbered input lines. No speculative quotes or severity inflation."""
    matches: list[dict[str, Any]] = []
    seen = set()
    for number, line in enumerate(log.splitlines(), 1):
        if not line.strip():
            continue
        for kind, label, severity, pattern in RULES:
            if pattern.search(line):
                if number not in seen:
                    matches.append({
                        "line": number,
                        "text": line.strip()[:220],
                        "type": kind,
                        "label": label,
                        "severity": severity,
                    })
                    seen.add(number)
                break
    matches.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["severity"]])
    selected = matches[:limit]
    priority = selected[0]["severity"] if selected else "info"
    return {
        "severity": priority,
        "signals_found": len(matches),
        "evidence": selected,
        "note": "Heuristic matches only; verify against the full log." if selected
                else "No known error signature detected; this does not prove the log is healthy.",
    }


def compare_logs(before: str, after: str, limit: int = 12) -> dict[str, Any]:
    """Exact line-based diff with source line numbers, bounded for small models."""
    a, b = before.splitlines(), after.splitlines()
    matcher = SequenceMatcher(a=a, b=b, autojunk=False)
    added, removed = [], []
    count_added = count_removed = 0
    for operation, a1, a2, b1, b2 in matcher.get_opcodes():
        if operation in {"replace", "delete"}:
            count_removed += a2 - a1
            for idx in range(a1, a2):
                if len(removed) < limit:
                    removed.append({"line": idx + 1, "text": a[idx][:220]})
        if operation in {"replace", "insert"}:
            count_added += b2 - b1
            for idx in range(b1, b2):
                if len(added) < limit:
                    added.append({"line": idx + 1, "text": b[idx][:220]})
    existing = {m["line"]: m for m in extract_evidence(after, limit=100)["evidence"]}
    introduced = []
    for item in added:
        signal = existing.get(item["line"])
        if signal is not None:
            introduced.append({**item, "label": signal["label"], "severity": signal["severity"]})
    return {
        "added_count": count_added,
        "removed_count": count_removed,
        "added": added,
        "removed": removed,
        "new_error_signals": introduced,
        "note": "Diff compares lines, not deployment causality. Confirm suspected regressions independently.",
    }
