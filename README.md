# 👻 Ghost Terminal AI

**Find the ghost in your logs.**

[![CI](https://github.com/hoangsvit/ghost-terminal-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/hoangsvit/ghost-terminal-ai/actions/workflows/ci.yml)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-8b5cf6.svg)](CONTRIBUTING.md)

**Ghost Terminal AI** is an open-source developer tool that helps you inspect application and deployment logs, compare runs, and investigate probable failures. It combines **deterministic log evidence** with **Gemma 3** running through **Ollama**, so you can start with a fast, model-free scan and optionally ask an open-weight model for a more detailed explanation.

It also includes a creative **Story** mode, originally built for the Hacktoberfest 2026 *Ghost in the Machine* challenge.

> **Important:** This is a debugging assistant, **not** an incident-response authority. Its error signatures are heuristics; Gemma-generated root causes and checks are hypotheses that must be independently verified. The app never executes commands from logs or applies suggested fixes.

## Contents

- [What can it do?](#what-can-it-do)
- [Try it locally](#try-it-locally)
- [Use the web interface](#use-the-web-interface)
- [API reference](#api-reference)
- [Deploy on Google Compute Engine](#deploy-on-google-compute-engine)
- [Architecture and project structure](#architecture-and-project-structure)
- [Configuration](#configuration)
- [Testing](#testing)
- [Privacy, security and limitations](#privacy-security-and-limitations)
- [Troubleshooting](#troubleshooting)
- [Contributing and support](#contributing-and-support)
- [License and acknowledgements](#license-and-acknowledgements)

## What can it do?

| Tool | When to use it | Requires Ollama? |
| --- | --- | --- |
| **Instant Scan** | Quickly identify common error signatures, severity indicators, exact source line numbers and cautious verification steps | **No** |
| **Analyze Logs** | Ask Gemma 3 to summarize a failure, propose a *possible* cause and explain what to check next | **Yes** |
| **Compare Logs** | Compare a previous/baseline log with a new run, inspect added/removed lines and request an AI interpretation | **Yes** for the AI button; **No** for Instant Scan in Compare mode |
| **Story** | Transform Git history or terminal output into original Haunting, Remembrance or Mystery fiction | **Yes** |

### Practical example

Paste this **synthetic**, non-sensitive log:

```text
[12:00:00] Starting Node.js application
[12:00:01] Checking dependencies
[12:00:02] Error: listen EADDRINUSE: address already in use :::3000
[12:00:03] Process exited with code 1
```

An **Instant Scan** can identify an `EADDRINUSE` signature, mark the relevant **original log line** and suggest checking which process is already listening on port 3000. **Analyze Logs** can then generate a more conversational, qualified explanation using Gemma 3. These checks are recommendations, not executed commands.

Other built-in synthetic scenarios include missing Python modules, out-of-memory container failures, full disks, region-policy restrictions, connection refusal, credential-redaction checks and logs without a recognized error. Compare mode includes deployment regressions and identical-log cases.

### Key design choices

- **Evidence first.** The Python backend extracts log matches and source line numbers; model-generated references are not trusted as proof.
- **Offline-friendly.** Instant Scan works without Ollama. After downloading a model, AI inference can run on your own machine without a paid AI API.
- **Compare with less noise.** The UI can ignore common *leading timestamp-only* changes. Source line numbers and shown log text remain unchanged.
- **Shareable output.** Copy the result or download a Markdown diagnostic report from the browser.
- **Original creative mode.** Story generation stays separate from technical diagnosis.

## Try it locally

### Requirements

- **Python 3.10+** — application and HTTP server use the Python standard library, with **no pip dependencies**.
- **Modern desktop or mobile browser** — the UI is HTML, CSS and vanilla JavaScript.
- **Ollama** — required only for AI Analyze, AI Compare and Story. `gemma3:1b` is the default model.
- **Node.js 20+** — only needed for the optional JavaScript checks in the contributor test suite. No `npm install` is needed for normal use.

### 1. Clone and launch

```bash
git clone https://github.com/hoangsvit/ghost-terminal-ai.git
cd ghost-terminal-ai
python3 app.py
```

On Windows, use `python app.py` if that is the command installed on your system.

Open **http://127.0.0.1:8765**. Select **Analyze**, choose **Port conflict — EADDRINUSE**, click **Load scenario**, then **Instant Scan**. This path does **not** require an AI model or an internet connection after installation.

The web server listens only on `127.0.0.1` by default. Do not expose the Python server directly to the public internet.

### 2. Enable Gemma 3 inference (optional)

Install [Ollama](https://ollama.com/download) for your operating system. Start the Ollama service if it is not already running, then download the model:

```bash
ollama pull gemma3:1b
ollama list
```

On systems without an automatically started Ollama service, run `ollama serve` in a separate terminal. Keep `python3 app.py` running and reload the browser. The model indicator should report readiness when the configured model is installed and reachable.

To use a larger model, first download it:

```bash
ollama pull gemma3:4b
```

Then start the app with `GHOST_MODEL=gemma3:4b` in its environment (for example, `GHOST_MODEL=gemma3:4b python3 app.py` in a Unix shell). Larger models require more resources. CPU-only inference, especially on a small VM, may be slow.

## Use the web interface

1. Select **Analyze**, **Compare**, or **Story**.
2. Choose a synthetic example from **TEST SCENARIOS** and click **Load scenario**, or paste your own **non-sensitive** log.
3. For **Analyze/Compare**, click **Instant Scan** for rule-based findings, or the main AI action to query Gemma 3. Story mode uses **Awaken the terminal**.
4. Inspect the **summary, possible cause, original evidence lines and suggested checks**. In Compare, also inspect the added and removed lines. The **Sample check** verifies selected structural signals, **not** whether the AI's diagnosis is accurate.
5. Use **Copy report** or **Markdown** to share a reviewed report. For Story, use the story copy control.

In Compare mode, load both **Baseline / Previous Log** and **Current / New Log**. The UI enables **Ignore timestamp-only changes** by default; the raw API leaves this option off unless explicitly requested.

**Input limits:** each log must be **6,000 characters or fewer** and **100 lines or fewer**. The HTTP request body is also limited to **25,000 bytes**. The server may return `400`, `413`, `415`, `429` or `503` for invalid input, oversized requests, unsupported content types, busy hosted inference or an unavailable model.

## API reference

The Python server exposes same-origin JSON endpoints. Examples below assume a **locally running** server and synthetic input.

| Method | Route | Purpose | Ollama |
| --- | --- | --- | --- |
| `GET` | `/api/health` | Model availability and deployment mode | Reports status; does not generate |
| `POST` | `/api/inspect` | Instant Scan, optionally with a baseline | Not required |
| `POST` | `/api/analyze` | AI diagnosis and deterministic evidence | Required |
| `POST` | `/api/compare` | AI interpretation of the previous and current logs | Required |
| `POST` | `/api/interpret` | Fictional story generation | Required |

**Quick scan:**

```bash
curl -fsS http://127.0.0.1:8765/api/inspect \
  -H 'Content-Type: application/json' \
  -d '{"log":"[12:00:00] Starting app\n[12:00:01] ERROR: EADDRINUSE"}'
```

**Compare without invoking the model:**

```bash
curl -fsS http://127.0.0.1:8765/api/inspect \
  -H 'Content-Type: application/json' \
  -d '{"baseline":"[11:00:00] Ready","log":"[12:00:00] ERROR: EADDRINUSE","ignore_timestamps":true}'
```

**AI diagnosis / AI comparison:**

```bash
curl -fsS http://127.0.0.1:8765/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"log":"ModuleNotFoundError: No module named fastapi"}'

curl -fsS http://127.0.0.1:8765/api/compare \
  -H 'Content-Type: application/json' \
  -d '{"baseline":"Worker started","log":"ERROR: ECONNREFUSED","ignore_timestamps":true}'
```

**Story:**

```bash
curl -fsS http://127.0.0.1:8765/api/interpret \
  -H 'Content-Type: application/json' \
  -d '{"log":"git commit -m \"restore the last light\"","mode":"haunting"}'
```

The story modes are `haunting`, `memory` (shown in the UI as *Remembrance*) and `mystery`.

The `/api/inspect` response includes `analysis`, `signals`, optional `diff`, `engine: "rules"` and a redaction count. AI diagnosis responses use `engine: "gemma3"` and also include the selected model. Diagnosis summaries and suggested checks are **not verified diagnoses**; severity comes from pattern matching, not a calibrated risk score.

`GET /api/health` returns fields including `ready`, `connected`, `model`, `message` and `deployment` (typically `local` or `vm`). A healthy model is one with `ready: true`; an HTTP 200 on its own is **not** proof that the model is available.

## Deploy on Google Compute Engine

The optional hosted configuration runs **Gemma 3 + Ollama on an Ubuntu Compute Engine VM**, with **Caddy** for HTTPS and the Python app bound to loopback. It does not use Cloud Run or a paid hosted AI API.

> **Costs and credentials:** Creating or starting a VM may incur charges for compute, persistent disks and public IP addresses. Temporary Qwiklabs projects may restrict Compute Engine, networking, IAM, quota or allowed zones. Hosting **does not make logs private**: inputs are sent from the browser to your VM. Never use the public demo with confidential production data.

### One command: create or update

The unified deployment flow is introduced by [PR #8](https://github.com/hoangsvit/ghost-terminal-ai/pull/8). **After that PR is merged into `main`**, run in Google Cloud Shell:

```bash
curl -fsSL https://raw.githubusercontent.com/hoangsvit/ghost-terminal-ai/main/vm/update.sh \
  -o /tmp/ghost-update.sh

bash /tmp/ghost-update.sh --project YOUR_PROJECT_ID --ref main
```

The project ID is **explicit** so the script does not accidentally act in another Qwiklabs project. Replace `YOUR_PROJECT_ID` with your own project ID.

- **No VM in the selected project:** the script can provision `ghost-terminal-ai-vm`, install Ollama and `gemma3:1b`, configure a restricted-to-tag firewall rule for ports **80/443**, set up Caddy HTTPS, and verify public model health. It does not silently interpret an IAM listing failure as an empty project.
- **Existing running VM:** it updates code from the selected Git ref without reinstalling model weights, checks local and public health, and retains the prior commit for rollback.
- **Existing stopped VM:** deploy mode starts it first; charges may resume.
- **Failure:** it reports missing permissions, quota, policy, initialization or HTTPS errors instead of claiming a working deployment. A failed first boot **does not automatically delete the VM**; inspect resources and costs.

The default VM configuration is **`e2-standard-2`** with a **30 GB boot disk**. It uses a public IPv4 address and a `<IP>.sslip.io` hostname; the hostname can change if the VM's ephemeral IP changes. A small global demo inference throttle is configured; this is **not** production-grade abuse prevention or a hard cost cap.

<details>
<summary>Preview the unmerged deployment PR before it reaches main</summary>

Use the script and application branch from the **same** feature PR:

```bash
curl -fsSL \
  https://raw.githubusercontent.com/hoangsvit/ghost-terminal-ai/fix/one-command-vm-deploy-and-update/vm/update.sh \
  -o /tmp/ghost-update.sh

bash /tmp/ghost-update.sh \
  --project YOUR_PROJECT_ID \
  --ref fix/one-command-vm-deploy-and-update
```

This can create or modify real GCP resources. Inspect the script before running it, and review the [PR checks](https://github.com/hoangsvit/ghost-terminal-ai/pull/8). Once the PR is merged, prefer `main`.

</details>

### Operations on an existing VM

After downloading the matching `vm/update.sh` script into Cloud Shell:

```bash
# Show the deployed commit and check local service/model health
bash /tmp/ghost-update.sh --project YOUR_PROJECT_ID --status

# Update code without permitting creation of a new VM
bash /tmp/ghost-update.sh --project YOUR_PROJECT_ID --no-create --ref main

# Restore the previously deployed commit, if one is recorded
bash /tmp/ghost-update.sh --project YOUR_PROJECT_ID --rollback
```

Pass `--zone ZONE` to select a known zone. The updater supports deployment from a reviewed Git branch using `--ref BRANCH`; a **PR merge does not trigger an automatic public VM deployment**.

See [DEPLOY_COMPUTE_ENGINE.md](DEPLOY_COMPUTE_ENGINE.md) for project permissions, initial setup, health checks, location policies, systemd logs, HTTPS troubleshooting, rollback and shutdown.

## Architecture and project structure

```text
Local:  Browser -> 127.0.0.1:8765 (Python HTTP) -> 127.0.0.1:11434 (Ollama)
Hosted: Browser -> HTTPS/Caddy -> 127.0.0.1:8765 -> 127.0.0.1:11434

                 +--> /api/inspect (deterministic rules; no AI)
Browser/API -----+--> /api/analyze and /api/compare (rules + Gemma 3)
                 +--> /api/interpret (creative Story + Gemma 3)
```

| Path | Responsibility |
| --- | --- |
| `app.py` | Standard-library HTTP server, routes, input checks and headers |
| `ghost_terminal/core.py` | Input cleaning/redaction, story prompts and output validation |
| `ghost_terminal/analysis.py` | Deterministic error signatures, source evidence, comparison, instant triage |
| `ghost_terminal/diagnosis.py` | Structured Gemma diagnosis and qualified recommendations |
| `ghost_terminal/ollama_client.py` | Loopback-only Ollama transport and health checks |
| `public/` | HTML, CSS, vanilla JS UI and synthetic test scenarios |
| `tests/` | Offline unit, HTTP integration, VM script and repository health tests |
| `vm/deploy.sh` | New VM provisioning and firewall/HTTPS bootstrap orchestration |
| `vm/startup.sh` | VM first-boot services, model install, Caddy and readiness |
| `vm/update.sh` | Unified VM create/update entrypoint, status and rollback |
| `docs/` | Feature, QA and maintainer guidance |

No database or server-side log history is included. Application and model responses are used in memory; the browser creates Markdown report downloads locally.

## Configuration

Environment variables read by the Python app and optional VM scripts:

| Variable | Default | Meaning |
| --- | --- | --- |
| `GHOST_PORT` | `8765` | Local web server port |
| `GHOST_MODEL` | `gemma3:1b` | Installed Ollama model tag |
| `GHOST_OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama endpoint; **loopback-only** URLs are accepted |
| `GHOST_INFERENCE_TIMEOUT` | `110` seconds | Model request timeout (bounded by code) |
| `GHOST_DEPLOYMENT` | `local` | `vm` enables hosted privacy disclosures and deployment status |
| `GHOST_RATE_LIMIT_PER_MINUTE` | `0` (unlimited locally) | Global, in-memory AI-generation throttle; VM sets `3` |
| `PROJECT_ID`, `ZONE`, `VM_NAME` | Active project / auto zone / `ghost-terminal-ai-vm` | Google Cloud deployment selectors |
| `REF` | `main` | Git branch selected for VM deployment |
| `MACHINE_TYPE` | `e2-standard-2` | Machine type when provisioning a new VM |

The app does **not** require an OpenAI, Gemini or Google Cloud AI API key. Google Cloud credentials are needed only when using the optional Compute Engine deployment workflow.

## Testing

Run the complete offline checks from the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q app.py ghost_terminal
node --check public/app.js
node --check public/scenarios.js
node --test tests/test_scenarios.cjs
bash -n vm/deploy.sh vm/startup.sh vm/update.sh
```

The test suite mocks model calls and Google Cloud operations where needed. **Passing CI does not establish real Gemma reasoning quality, TLS availability, deployment permissions or mobile UI correctness.** Always test the actual model and live HTTPS after a deliberate deployment.

[GitHub Actions](https://github.com/hoangsvit/ghost-terminal-ai/actions) runs tests on pull requests and `main`; there is **no automatic VM deployment** in CI.

## Privacy, security and limitations

- **Do not paste secrets or private production logs into any public demo.** On hosted mode, the browser transmits the original log over HTTPS to the VM **before** server-side sanitization.
- Server-side redaction recognizes a limited set of common credentials (for example, certain tokens, passwords and bearer headers). It is **best effort**, not full anonymization. Exported reports may still contain information you should remove before sharing.
- The system treats logs as untrusted data, but prompt injection remains possible. AI-generated checks should be reviewed, never blindly executed.
- Evidence line numbers come from the sanitized source; heuristics cannot discover every failure, and **no detected error is not proof of a healthy system**.
- Model conclusions are not calibrated probabilities or verified root causes. The app does not run suggested commands or change the user's infrastructure.
- The public demo has no authentication, per-user isolation, audit trail or hard usage-cost cap. Do not deploy it as a multi-tenant production incident service without additional controls.
- The project provides **no uptime guarantee or incident response SLA**. Temporary Qwiklabs projects and their `sslip.io` URLs can expire.

For private vulnerability disclosures, read [SECURITY.md](SECURITY.md), not public issue comments.

## Troubleshooting

| Symptom | First checks |
| --- | --- |
| `/api/health` returns `ready: false` | Confirm Ollama is running, `ollama list` contains `GHOST_MODEL`, and its endpoint is local |
| **Instant Scan works; AI Analyze/Story fails** | Check model readiness and inference timeout; on VM, inspect `journalctl -u ollama` and `journalctl -u ghost-terminal` |
| HTTP `429` | The public VM's **global** inference limit was reached; retry later. Instant Scan does not consume AI quota |
| HTTP `400` / `413` | Check log length, required baseline in Compare mode and request size |
| Deploy finds **0 VMs** in a new project | After PR #8, deploy mode provisions a VM unless `--no-create` was specified; verify `--project` points to the intended account/project |
| Deploy receives `PERMISSION_DENIED` or policy/quota errors | Verify cloud IAM/API, allowed zones, Compute Engine quota and billing/lab restrictions; the script does not bypass organization policy |
| HTTPS URL doesn't load | Check the external IP, Caddy certificate logs, DNS resolution, and inbound 80/443 on the tagged VM |
| VM or Cloud Shell session disappears | Qwiklabs resources may expire. Check the intended project and VM status before trying to create a replacement |

Detailed runbook: [Compute Engine deployment guide](DEPLOY_COMPUTE_ENGINE.md). For non-sensitive support requests, see [SUPPORT.md](SUPPORT.md).

## Contributing and support

Contributions from first-time and experienced developers are welcome. Before proposing a large feature, check [open issues](https://github.com/hoangsvit/ghost-terminal-ai/issues) to avoid duplicate work.

- [**Contributing guide**](CONTRIBUTING.md) — fork, branch, local checks, testing standards and PR process.
- [**Report a bug / request a feature / ask a question**](https://github.com/hoangsvit/ghost-terminal-ai/issues/new/choose) — structured GitHub issue forms.
- [**Open a pull request**](https://github.com/hoangsvit/ghost-terminal-ai/pulls) — include a reproduction, checks, safety review and screenshots when UI changes.
- [**Code of Conduct**](CODE_OF_CONDUCT.md) — respectful project participation.
- [**Security policy**](SECURITY.md) — private vulnerability reporting guidance.
- [**Support**](SUPPORT.md) — help with installation and non-sensitive issues.
- [**Change history**](CHANGELOG.md) and [**maintenance guidelines**](docs/REPOSITORY_MAINTENANCE.md) — release and triage practices.

The source is reviewed through pull requests; maintainers decide when to merge. A merged PR is **not** an instruction to run cloud deployment.

## License and acknowledgements

Project source code is available under the [**MIT License**](LICENSE). **Ollama** and **Google's Gemma model weights** have their own terms and licenses; the repository MIT license does not replace those terms.

Ghost Terminal AI began as a creative experiment for [Hacktoberfest 2026 — DEV Challenge Week 4](https://dev.to/challenges/hacktoberfest-week4-2026-10-26) and has since expanded into a practical log-investigation prototype. The optional Story mode preserves that origin.

For contest-related materials, see [DEV.to submission draft](DEVTO_SUBMISSION.md) and [final submission checklist](FINAL_SUBMISSION_CHECKLIST.md). Do not present code added after the contest deadline as though it existed during the challenge.

---

**Every log leaves a clue. Not every clue is a confirmed cause.**
