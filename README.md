# 👻 Ghost Terminal AI

**Find the ghost in your logs.** Open-weight **Gemma 3** via **Ollama** now explains software failures, compares CI/deployment logs, and optionally turns terminal history into fiction. Works locally or on a user-hosted Compute Engine VM.

Created for **Hacktoberfest 2026 • DEV Challenge Week 4: Ghost in the Machine** (Oct 26–31, 2026).

## What does it do?

**Analyze (default):** paste a stack trace, CI log or deployment output. The service extracts recognizable error signatures with exact source line numbers; Gemma 3 explains likely causes and suggests *verification steps*, not automatic fixes.

**Compare:** paste a current and previous deployment log. The Python backend computes an exact line diff; Gemma 3 summarizes the changed behavior and potential regressions.

**Story:** retain the original Haunting, Remembrance and Mystery creative writing modes. This experiment remains part of the Hacktoberfest theme.

**Important:** rule-based scans report heuristic matches, while AI conclusions are *hypotheses*, not incident root causes proven by a model. Evidence is assembled deterministically from the sanitized input, not AI-invented citations. Compare detects line changes, not necessarily causal changes.

This is **real AI inference, not a simulated response**. Generation requires a downloaded Gemma model and Ollama running. No hosted AI account or paid API is needed.

## Features

- **Instant Scan (no AI):** get recognized error signatures, exact source line numbers and cautious, read-only next checks without Ollama, latency or inference quota. Uses a new `POST /api/inspect` endpoint.
- **Timestamp-aware Compare:** optional “Ignore timestamp-only changes” normalizes common leading timestamps for diff matching, while keeping original log lines in results.
- **Markdown export:** download a report for issues or incident notes, generated locally in the browser from the sanitized response (no server-side report history).

- **Analyze Logs** with probable causes, severity heuristics, numbered evidence and safe checks
- **Compare Logs** using an exact server-side line diff and AI interpretation
- **Story**: three original storytelling frequencies: Haunting, Remembrance, Mystery
- Open-weight Gemma 3 inference via Ollama's local HTTP API
- Backend bound to `127.0.0.1`; only loopback Ollama hosts accepted
- Best-effort redaction of common tokens and passwords prior to inference
- Verified evidence echoes (hallucinated source quotes are filtered out)
- Responsive, keyboard-friendly dark UI, example log, one-click copy
- Pure Python standard library; no npm or pip install required
- Offline unit and HTTP integration tests using mock model responses

## Quick start

Install [Python 3.10+](https://python.org/downloads/) and [Ollama](https://ollama.com/download). Then run:

```bash
ollama pull gemma3:1b
python app.py
```

For **Instant Scan**, Ollama is optional: run `python app.py` and open **http://127.0.0.1:8765**. Choose a scenario and click **Instant Scan**. It works without model inference; logs are still sent to whichever server is hosting the site.

For **AI Analyze**, **AI Compare**, and **Story**, keep Ollama running and use **Analyze logs**, **Compare runs**, or **Awaken the terminal**. For before/after comparison, check **Ignore timestamp-only changes** to avoid noise from changing clock values.

For a larger model, run `ollama pull gemma3:4b`, then set `GHOST_MODEL=gemma3:4b` in your environment.

The first model generation may be slow. Only the model download requires internet; inference then works offline. Never expose the local Ollama endpoint publicly.

## How it works

```text
Browser (HTML + CSS + JS)
  -> POST /api/inspect (deterministic Instant Scan) or /api/analyze, /api/compare, /api/interpret
Python stdlib server (127.0.0.1:8765)
  -> validate input and redact obvious secrets
  -> Analyze: deterministic error heuristics + numbered source evidence
  -> Compare: deterministic before/after line diff
  -> JSON-schema prompt + local Ollama /api/generate
Gemma 3 (open-weight AI) -> diagnosis and verification steps OR creative story
  -> model output shown as an unverified hypothesis; evidence comes from source
  -> display via DOM textContent (without executing input)
```

The server never executes input logs, sends analytics, or persists the provided content. In a hosted VM demo, pasted log text travels to the VM; redaction currently occurs on the server before inference, **not before transmission**. Redaction is **best effort**, not guaranteed; avoid pasting sensitive information.

## Testing

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py ghost_terminal
```

Offline unit/integration tests cover input validation, deterministic evidence, line differences, common secret redaction, local-host restriction, model schemas, HTTP handling and fake-model end-to-end behavior. These tests do **not** verify model quality or the performance of a live Ollama instance.

## Optional Google Compute Engine VM deployment

The [Compute Engine VM guide](DEPLOY_COMPUTE_ENGINE.md) packages **the same Gemma 3 + Ollama** on an Ubuntu VM with automatic HTTPS. No Cloud Run or paid AI API is needed. Hosted input reaches your Google Cloud VM; avoid real private logs. The original local app is unchanged.

## Demo and contest

For the DEV Week 4 challenge, record a **real Gemma 3 generation demo** (video or screen recording). A UI mockup alone is not enough to demonstrate model inference.

Read [DEVTO_SUBMISSION.md](DEVTO_SUBMISSION.md) for an English submission draft and [FINAL_SUBMISSION_CHECKLIST.md](FINAL_SUBMISSION_CHECKLIST.md) for submission steps. Replace placeholders with actual links before posting.

Official contest page: https://dev.to/challenges/hacktoberfest-week4-2026-10-26

## Privacy and security notes

Logs are in memory while inferred. The app has no cloud fallback, no analytics and no server-side history. Input is untrusted data, not instructions, but prompt injection is still possible. Evidence lines are taken directly from sanitized source, but model conclusions are **not verified diagnoses**. Suggested checks require human review and are never executed. The story mode is fiction.

## License

[MIT License](LICENSE). Gemma model weights and Ollama have separate terms and licenses.

If code changes are made after October 31, 2026, disclose the post-deadline changes in this README rather than presenting them as contest-period work.
