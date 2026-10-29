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


# Timestamp-only differences are typically irrelevant in before/after deployment comparisons.
# Preserve all original text/line numbers when reporting concrete changes.
_TIMESTAMP_PREFIXES = (
    re.compile(r"^\[\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\]\s*"),
    re.compile(r"^\[\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?\]\s*"),
    re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?\s+"),
)


def _comparison_key(line: str, ignore_timestamps: bool) -> str:
    if not ignore_timestamps:
        return line
    for pattern in _TIMESTAMP_PREFIXES:
        replaced = pattern.sub("", line, count=1)
        if replaced != line:
            return replaced
    return line


def compare_logs(before: str, after: str, limit: int = 12, *,
                 ignore_timestamps: bool = False) -> dict[str, Any]:
    """Exact or timestamp-normalized diff, always showing original source line numbers."""
    a, b = before.splitlines(), after.splitlines()
    a_keys = [_comparison_key(x, ignore_timestamps) for x in a]
    b_keys = [_comparison_key(x, ignore_timestamps) for x in b]
    matcher = SequenceMatcher(a=a_keys, b=b_keys, autojunk=False)
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
            introduced.append({**item, "label": signal["label"], "severity": signal["severity"], "type": signal["type"]})
    return {
        "added_count": count_added,
        "removed_count": count_removed,
        "added": added,
        "removed": removed,
        "new_error_signals": introduced,
        "ignore_timestamps": ignore_timestamps,
        "note": (
            "Line differences ignore common leading timestamp formats; original line text retained. "
            "A change is not proof of causality." if ignore_timestamps
            else "Diff compares lines, not deployment causality. Confirm suspected regressions independently."
        ),
    }


# Conservative, read-only checks for a useful fast response when Gemma is unavailable.
# Do not turn model suggestions into executed commands.
_TRIAGE_CHECKS = {
    "resource": [
        "Inspect available disk space and inode usage for the affected filesystem.",
        "Identify which build artifacts or logs are consuming space.",
    ],
    "memory": [
        "Inspect process/container memory usage and OOM kill events.",
        "Compare memory limits and peak consumption around the failure.",
    ],
    "network": [
        "Confirm the destination host, port, and expected listening process.",
        "Inspect service status and recent connection errors.",
    ],
    "permission": [
        "Check the owner and permissions of the affected file or service.",
        "Compare the executing account with the required access policy.",
    ],
    "authentication": [
        "Confirm the configured identity, permissions, and token expiry without printing secrets.",
        "Check recent access-denied events and the target service policy.",
    ],
    "dependency": [
        "Confirm the dependency appears in the project manifest or lockfile.",
        "Compare the deployed environment and package installation output.",
    ],
    "deployment": [
        "Inspect the project organization policies and permitted deployment locations.",
        "Compare the target region with supported service regions.",
    ],
    "runtime": [
        "Read the full exception and stack trace immediately before the failure.",
        "Check recent code and environment changes related to the failing function.",
    ],
    "build": [
        "Inspect the first failing build step and its complete error output.",
        "Compare dependency versions and build environment with the last successful run.",
    ],
    "http": [
        "Inspect upstream application and proxy logs near the failed request.",
        "Check upstream health and recent deployments without exposing request secrets.",
    ],
    "generic": [
        "Inspect the log lines directly before and after the reported error.",
        "Check service state and the latest deployment changes.",
    ],
}


def quick_triage(log: str, *, baseline: str | None = None,
                 ignore_timestamps: bool = False) -> dict[str, Any]:
    """Rule-only findings without Ollama, remote calls or speculative AI analysis."""
    signals = extract_evidence(log)
    diff = (compare_logs(baseline, log, ignore_timestamps=ignore_timestamps)
            if baseline is not None else None)
    evidence = signals["evidence"]
    introduced = diff["new_error_signals"] if diff else []
    focus = introduced[0] if introduced else (evidence[0] if evidence else None)
    if focus:
        label = focus["label"]
        summary = (f"{signals['signals_found']} known error signal(s) in the current log. "
                   f"First prioritized match: {label} on line {focus['line']}.")
        probable_cause = (f"The input contains a pattern classified as '{label}'. "
                          "This is an indicator, not a confirmed root cause. Check its surrounding context.")
        checks = list(_TRIAGE_CHECKS.get(focus["type"], _TRIAGE_CHECKS["generic"]))
    else:
        summary = "No known error signature was detected in the supplied log."
        probable_cause = ("The root cause cannot be inferred from this sample. "
                          "Absence of known patterns does not prove a successful or healthy run.")
        checks = [
            "Collect the full failure context and relevant service logs.",
            "Check the application health and compare against a known-good execution.",
        ]
    if diff is not None:
        summary += (f" Compared with the previous run: {diff['added_count']} line(s) added, "
                    f"{diff['removed_count']} removed.")
        if diff["added_count"] == 0 and diff["removed_count"] == 0:
            summary += " No meaningful differences were found under the chosen comparison setting."
    return {
        "analysis": {
            "summary": summary,
            "probable_cause": probable_cause,
            "checks": checks,
            "confidence": "rule-based",
            "confidence_note": "Instant heuristic scan; no AI model was called.",
        },
        "signals": signals,
        "diff": diff,
        "engine": "rules",
    }
