# Ghost Terminal AI 2.0 — Functional acceptance checklist

## What changed?
The same violet-themed single-page web UI now has three modes:

| Tool | Endpoint | Main output |
|---|---|---|
| Analyze (default) | POST \`/api/analyze\` | AI summary, probable cause, evidence line numbers, suggested verification |
| Compare | POST \`/api/compare\` | Same diagnosis plus exact before/after line diff |
| Story | POST \`/api/interpret\` | Original Haunting, Remembrance and Mystery story |

All inputs are sanitized using \`prepare_input\` before inference or comparison. The API limits log length to 6,000 characters and 100 lines **per log**. A public VM demo uses an in-memory per-instance inference throttle (3 AI generations/min) and does not persist logs.

### Evidence and confidence
- Python matches known error signatures (disk full, OOM, EADDRINUSE, permissions, missing dependency, Cloud Run location policy, network timeouts, runtime exceptions, build failures, HTTP 5xx).
- Evidence includes the **actual line number and truncated text of the sanitized log**.
- The AI returns a short hypothesis and suggested checks. No AI-generated line numbers are trusted.
- The confidence label is deliberately bounded to \`medium\` when heuristics match and \`low\` when they do not. Do not interpret it as calibrated statistical certainty.
- Neither AI answers nor user-supplied log commands are automatically executed.

### Test scenarios directly on the website

Choose **Analyze**, **Compare**, or **Story**. A compact TEST SCENARIOS selector appears above the log editor.

Select a scenario, read its **Expected** result, then click **Load scenario**. For Compare, both the previous and current logs are populated. Selecting or loading alone never calls Gemma 3. Press the action button to run the real model.

After a successful response, the page shows a **Sample check** comparing deterministic error signatures, severity, selected source line numbers and any line differences against the selected sample. This does **not** certify the accuracy of model-generated reasoning.

The samples cover port collisions, missing Python dependencies, OOM, disk full, Google Cloud region policy, network faults, synthetic redaction checks, no-error uncertainty, deployment comparisons and storytelling. All logs are fictional. The catalog is in `public/scenarios.js` and checked by `node --test tests/test_scenarios.cjs`.

### Manual test
1. Open the site. **Analyze** must be selected by default.
2. Click **Load example**; a synthetic Node.js \`EADDRINUSE\` log appears.
3. Click **Analyze logs**; confirm the report shows error evidence on the correct original line and a qualified probable cause.
4. Switch to **Compare**, click **Load example** to fill both logs, then **Compare runs**. Verify the added error line and removed success line.
5. Switch to **Story**, click **Load example**, choose **Haunting**, then **Awaken the terminal**; original story flow should still work.
6. On a mobile screen, check tabs, both text fields and report readability. Check Copy report.
7. Check cross-origin rejection and input limits by running the Python tests.

### Tests
\`\`\`bash
python3 -m unittest discover -s tests -v
node --check public/app.js
node --test tests/test_scenarios.cjs
bash -n vm/startup.sh
\`\`\`

**Important:** These tests are offline and mock Ollama; a real Gemma 3 response must be verified on the running VM before claiming production readiness.

## Test PR #4 on the existing VM without creating new infrastructure

**Do this only after approving the PR code.** VM: \`ghost-terminal-ai-vm\`; project: \`qwiklabs-gcp-01-dc59a1a9e903\`; zone: \`us-east1-d\`.

First inspect the repository for local changes. Do not discard uncommitted user modifications:

\`\`\`bash
gcloud compute ssh ghost-terminal-ai-vm --project=qwiklabs-gcp-01-dc59a1a9e903 --zone=us-east1-d \
  --command='sudo -u ghostapp -H git -C /opt/ghost-terminal-ai status --short'
\`\`\`

When the output is empty, use an SSH shell to switch to the reviewed PR code. No build, new VM or new Ollama download is needed:

\`\`\`bash
sudo -u ghostapp -H git -C /opt/ghost-terminal-ai fetch origin feature/ghost-terminal-2-log-analyzer
sudo -u ghostapp -H git -C /opt/ghost-terminal-ai switch --detach FETCH_HEAD
sudo systemctl restart ghost-terminal
curl -fsS http://127.0.0.1:8765/api/health
\`\`\`

Visit the **existing** VM HTTPS address and perform all three modes. To roll back:

\`\`\`bash
sudo -u ghostapp -H git -C /opt/ghost-terminal-ai switch feature/compute-engine-vm-gemma3
sudo systemctl restart ghost-terminal
\`\`\`

Public VM URL is temporary because the current Google Cloud project is a Qwiklabs lab. Never paste production logs or secrets in a public demo, even with best-effort redaction.
