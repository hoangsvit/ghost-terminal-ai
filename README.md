# 👻 Ghost Terminal AI

[![CI](https://github.com/hoangsvit/ghost-terminal-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/hoangsvit/ghost-terminal-ai/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)


**Find the ghost in your logs.** Open-weight **Gemma 3** via **Ollama** now explains software failures, compares CI/deployment logs, and optionally turns terminal history into fiction. Works locally or on a user-hosted Compute Engine VM.

Created for **Hacktoberfest 2026 • DEV Challenge Week 4: Ghost in the Machine** (Oct 26–31, 2026).

## Community and contributions

Ghost Terminal AI is open source under the **[MIT License](LICENSE)**. Contributions, bug reports, questions and improvement proposals are welcome.

- **Start contributing:** [CONTRIBUTING.md](CONTRIBUTING.md) — local setup, test commands, code standards and PR process.
- **Create an issue:** [Bug / Feature / Docs / Question](https://github.com/hoangsvit/ghost-terminal-ai/issues/new/choose) — structured templates and synthetic examples.
- **Submit code:** [Pull requests](https://github.com/hoangsvit/ghost-terminal-ai/pulls) — fork, work on a branch, run checks and open a PR targeting `main`.
- **Community behavior:** [Code of Conduct](CODE_OF_CONDUCT.md).
- **Report vulnerabilities privately:** [SECURITY.md](SECURITY.md) — never publish exploits or real secrets in issues.
- **Get help:** [SUPPORT.md](SUPPORT.md).
- **Maintainer workflow:** [Repository maintenance guide](docs/REPOSITORY_MAINTENANCE.md).
- **Change history:** [CHANGELOG.md](CHANGELOG.md).

No public demo or CI run should be treated as proof that AI output is a verified technical diagnosis. Never share private production logs or credentials.

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

For contributing and repository health checks (Python, Node and VM scripts), see [CONTRIBUTING.md](CONTRIBUTING.md).

Offline unit/integration tests cover input validation, deterministic evidence, line differences, common secret redaction, local-host restriction, model schemas, HTTP handling and fake-model end-to-end behavior. These tests do **not** verify model quality or the performance of a live Ollama instance.

## One-command Google Cloud deploy (new or existing VM)

Run this in **Google Cloud Shell** using the intended project. This is the same command for a fresh Qwiklabs project and for an existing `ghost-terminal-ai-vm`:

```bash
curl -fsSL https://raw.githubusercontent.com/hoangsvit/ghost-terminal-ai/main/vm/update.sh -o /tmp/ghost-update.sh
bash /tmp/ghost-update.sh --project YOUR_PROJECT_ID --ref main
```

- **No VM in that project:** provisions a new Compute Engine VM, persistent disk, Ollama/Gemma 3 and Caddy HTTPS, then verifies the public `/api/health`.
- **VM already exists:** updates application code to the requested Git branch, restarts the app, checks model health and verifies public HTTPS; no reinstall.
- **VM stopped:** starts the existing VM in deploy mode (billing may resume).
- **Insufficient permissions, prohibited zones/quota, TLS or model startup failures:** exits with an actionable error instead of reporting success. New VM resources are **preserved**, not destroyed, if first boot fails.

Creating/running a VM, disk and public IPv4 can incur charges. Qwiklabs projects may expire or restrict VM creation. Use `--no-create` to prohibit creating new resources, `--status` to check an existing VM, and `--rollback` to revert application code. **Nothing deploys automatically from a PR merge.**

More commands, alternate-zone selection, checks and troubleshooting: [Compute Engine guide](DEPLOY_COMPUTE_ENGINE.md).

## Fast updates for an existing VM

The updater is also suitable for an existing VM. In Google Cloud Shell:

```bash
bash vm/update.sh --ref main
```

Preview an unmerged PR branch without merging it:

```bash
bash vm/update.sh --ref feature/my-reviewed-change
```

Check service/model health with `bash vm/update.sh --status` and revert to the previous deployed commit with `bash vm/update.sh --rollback`. Project and VM zone are detected automatically. Override with `--project PROJECT_ID --zone ZONE` when necessary.

For Cloud Shell without a repository checkout, download the script from the branch you plan to test, review it, then run it:

```bash
curl -fsSL https://raw.githubusercontent.com/hoangsvit/ghost-terminal-ai/main/vm/update.sh -o /tmp/ghost-update.sh
bash /tmp/ghost-update.sh --ref main
```

**Safety:** The updater now creates a VM **only when none exists in the selected project**, unless `--no-create` is set. Existing VM updates preserve Ollama/model weights, reject uncommitted changes, and attempt rollback after unhealthy code updates. New VM initialization may require Compute Engine API, quota and firewall permissions. Switching branches on the VM changes the live website; do this only when you intend to preview/deploy. Qwiklabs VMs and sslip.io URLs may expire with the lab.

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
