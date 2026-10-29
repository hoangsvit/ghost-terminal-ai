# 👻 Ghost Terminal AI

**Every log leaves a haunting.** A privacy-first storytelling studio that transforms command history, build logs, and old Git commits into original microfiction using **Gemma 3**, an open-weight model, through **Ollama**, running locally.

Created for **Hacktoberfest 2026 • DEV Challenge Week 4: Ghost in the Machine** (Oct 26–31, 2026).

## What does it do?

Paste a terminal log, choose **Haunting**, **Remembrance**, or **Mystery**, and generate a new fictional story inspired by technical traces. Gemma 3 performs the narrative generation locally, returns structured JSON, and the app discards invented quotes not present in the input.

This is **real AI inference, not a simulated response**. Generation requires a downloaded Gemma model and Ollama running. No hosted AI account or paid API is needed.

## Features

- Three original storytelling frequencies: Haunting, Remembrance, Mystery
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

Keep Ollama running and open **http://127.0.0.1:8765** in your browser. Click **Load sample log** and then **Awaken the terminal**.

For a larger model, run `ollama pull gemma3:4b`, then set `GHOST_MODEL=gemma3:4b` in your environment.

The first model generation may be slow. Only the model download requires internet; inference then works offline. Never expose the local Ollama endpoint publicly.

## How it works

```text
Browser (HTML + CSS + JS)
  -> POST /api/interpret
Python stdlib server (127.0.0.1:8765)
  -> validate input and redact obvious secrets
  -> JSON-schema prompt + local Ollama /api/generate
Gemma 3 (open-weight AI) -> title + story + final whisper + echoes
  -> validate echoes against redacted source
  -> display via DOM textContent (without executing input)
```

The local server never executes input logs, sends analytics, or persists the provided content. Redaction is **best effort**, not guaranteed; avoid pasting sensitive information.

## Testing

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py ghost_terminal
```

19 offline unit/integration tests cover input validation, common secret redaction, local-host restriction, model schema, HTTP handling and fake-model end-to-end behavior. These tests do **not** verify model quality or the performance of a live Ollama instance.

## Optional public cloud demo\n\nWant an HTTPS demo for DEV.to without running Ollama on the visitor's laptop? The [Cloudflare Workers AI deployment guide](DEPLOY_CLOUDFLARE.md) runs **Gemma 4** on Cloudflare while preserving the original **local Gemma 3** app. Hosted requests are sent to Cloudflare; **never upload sensitive logs**.\n\n## Demo and contest

For the DEV Week 4 challenge, record a **real Gemma 3 generation demo** (video or screen recording). A UI mockup alone is not enough to demonstrate model inference.

Read [DEVTO_SUBMISSION.md](DEVTO_SUBMISSION.md) for an English submission draft and [FINAL_SUBMISSION_CHECKLIST.md](FINAL_SUBMISSION_CHECKLIST.md) for submission steps. Replace placeholders with actual links before posting.

Official contest page: https://dev.to/challenges/hacktoberfest-week4-2026-10-26

## Privacy and security notes

Logs are in memory while inferred. The app has no cloud fallback, no analytics and no server-side history. Input is untrusted data, not instructions, but prompt injection is still possible. Quotes are checked against source; model output is fiction, **not** an account of real incidents.

## License

[MIT License](LICENSE). Gemma model weights and Ollama have separate terms and licenses.

If code changes are made after October 31, 2026, disclose the post-deadline changes in this README rather than presenting them as contest-period work.
