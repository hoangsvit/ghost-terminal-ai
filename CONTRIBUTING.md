# Contributing to Ghost Terminal AI

Thanks for helping make open-weight log analysis more useful and trustworthy. Contributions of bug reports, documentation, test fixtures, accessibility improvements, and code are welcome.

By participating, you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md). This project is MIT-licensed; see [LICENSE](LICENSE). Gemma model weights and Ollama are separate projects with their own terms.

## Find the right starting point

- **Bug:** open a [Bug report](https://github.com/hoangsvit/ghost-terminal-ai/issues/new/choose) after searching existing issues. Include expected vs actual behavior, steps to reproduce, and sanitized sample logs.
- **New feature:** open a Feature request and explain the real user problem, proposed scope, alternatives, and acceptance criteria.
- **Docs or question:** use the corresponding issue form. Small typo/documentation fixes can go straight to a PR.
- **Security vulnerability:** follow [SECURITY.md](SECURITY.md); never post exploits, credentials, or confidential logs publicly.

Before major refactors or breaking API changes, discuss the proposal in an issue so contributors do not duplicate effort. Maintainers may prioritize work based on practical impact, safety, and scope.

## Set up development

**Requirements:** Python 3.10+ and Node.js 20+ (Node is used only for JavaScript syntax and scenario tests; no npm install or frontend build is required).

1. Fork the repository, clone your fork, and create a descriptive branch from the latest `main`:

   ```bash
   git clone https://github.com/YOUR_GITHUB_USERNAME/ghost-terminal-ai.git
   cd ghost-terminal-ai
   git remote add upstream https://github.com/hoangsvit/ghost-terminal-ai.git
   git fetch upstream
   git switch -c fix/describe-the-problem upstream/main
   ```

2. Run the server: `python3 app.py`; open `http://127.0.0.1:8765`.
   - **Instant Scan** needs no model.
   - **Analyze**, **Compare** and **Story** require Ollama and a downloaded Gemma model: `ollama pull gemma3:1b`. Start Ollama on `127.0.0.1:11434`; do not expose it publicly.
3. Use synthetic samples from the in-browser scenario picker. **Never paste private credentials, production logs, or customer data into issues or the public demo.**

## Run the checks before opening a PR

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q app.py ghost_terminal
node --check public/app.js
node --check public/scenarios.js
node --test tests/test_scenarios.cjs
bash -n vm/deploy.sh vm/startup.sh vm/update.sh
```

CI runs an offline version of these checks. Mocked-model tests do **not** establish real Gemma quality. If you change model prompts, include a representative sanitized input and describe your manual Ollama test separately.

## Where to contribute

| Path | Purpose |
| --- | --- |
| `app.py` | Python standard-library HTTP routes, input validation and response handling |
| `ghost_terminal/core.py` | Sanitization, story prompts and schema validation |
| `ghost_terminal/analysis.py` | Deterministic error signals, source evidence and diff |
| `ghost_terminal/diagnosis.py` | AI diagnostic prompt and structured output |
| `ghost_terminal/ollama_client.py` | Loopback-only Ollama transport |
| `public/` | Accessible browser UI, scenario picker and styles |
| `tests/` | Unit, integration, security and scenario regression tests |
| `vm/` | Optional Compute Engine deployment/update scripts |

Keep changes focused. Prefer Python stdlib and vanilla JavaScript, consistent with the project's zero-package app architecture. New dependencies need a justification, pinned/reproducible installation instructions, appropriate licenses, and CI coverage.

### Grounding and privacy requirements

- Never fabricate evidence, line numbers or confirmed diagnoses. AI suggestions are hypotheses and must be labeled as such.
- Treat log text as **untrusted data**, never as executable commands or system instructions.
- Render external/model data as text (`textContent`), not unsanitized HTML.
- Reuse `prepare_input` for new server endpoints and enforce per-log size limits.
- Redaction is **best effort** and currently occurs on the server; hosted users still send input to that server. Do not claim browser-side secrecy or guaranteed anonymization.
- Do not add telemetry, storage, new public endpoints or automatic command execution without discussing the privacy and security impact.
- Include tests demonstrating the fix and (when relevant) failure behavior, not only success cases.

## Submit a pull request

1. Commit on your feature branch (descriptive messages such as `fix: correct missing-module signal`).
2. Push to your fork, then open a PR **against `main`**, referencing the issue (`Fixes #123` when appropriate).
3. Complete the [PR checklist](.github/PULL_REQUEST_TEMPLATE.md): what/why, tested commands, screenshots for UI changes, compatibility and security considerations.
4. Address review and CI feedback. Avoid unrelated formatting or generated files, and do not force-push branches maintained by other contributors.
5. Maintainers decide whether/when to merge. **Opening a PR never deploys the public VM.** Deployment requires a separate reviewed action.

## Review and releases

Maintainers check correctness, safety, tests, clarity, and project fit. A passing CI is necessary but may not be sufficient for merging. Breaking behavior or schema changes should be documented and may require migration notes. See [maintenance guidance](docs/REPOSITORY_MAINTENANCE.md) for repository settings and optional release workflow.

Thanks for contributing!
