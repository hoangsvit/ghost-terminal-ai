# Ghost Terminal AI — Next practical improvements

This proposal is intentionally small and reviewable. It adds useful functionality without changing the existing deployment architecture.

## Implemented in this PR

### 1. Instant Scan — works without Gemma

**Analyze / Compare → Instant Scan** calls \`POST /api/inspect\`, not Ollama. It uses the existing server-side sanitizer and deterministic error rules, returning a report in the same format as AI Analyze. No inference quota is consumed, and it works even when Gemma is offline.

Example:

\`\`\`text
[12:00:01] Listening on port 3000
[12:00:02] ERROR: EADDRINUSE
\`\`\`

Expected: HIGH severity, an error cited at **L2**, cautious wording and safe checks. It is a heuristic, not verified root-cause analysis.

### 2. Timestamp-aware Compare

Check **Ignore timestamp-only changes** to prevent clock changes from inflating the before/after diff. Matching only strips a leading bracketed \`HH:MM:SS\` time or standard ISO-style datetime prefix. The visible evidence retains **original** line numbers and texts. The check is on by default in the UI; the API default is **false** to preserve prior clients.

Before: \`[12:00:01] Worker ready\`
After: \`[12:05:10] Worker ready\`
Expected: **0 added, 0 removed** with the option enabled. If the message itself changes, the diff still reports it.

### 3. Download Markdown report

After AI Analyze, Compare or Instant Scan, click **Markdown**. The browser creates \`ghost-terminal-report.md\` containing summary, hypotheses/heuristics, safe checks, bounded log evidence and original diff lines. No server file or database is created.

Do not assume report output is fully anonymized: server redaction is best-effort and can miss passwords.

## Manual verification on the live VM

Once the code has been reviewed and explicitly deployed:

1. In **Analyze**, load \`Port conflict — EADDRINUSE\`, then click **Instant Scan**. It should work without waiting for Gemma; sample checks should pass.
2. Click **Analyze logs** on the same input; compare cautious AI diagnosis with rule-based findings.
3. In **Compare**, load \`Deployment — success to failure\`. Run **Instant Scan** and verify the newly introduced EADDRINUSE is cited. Toggle timestamp handling and compare counts.
4. Test two logs whose only difference is the bracketed timestamp. With the option on, there should be no changes.
5. Try the \`No obvious error\` case: report must express uncertainty instead of fabricating a root cause.
6. Download the Markdown report. Confirm it contains no obvious synthetic password from the redaction sample and includes original line numbers.
7. Check responsive layout at mobile width and all three tabs.
8. Test the HTTP endpoint with \`python -m unittest discover -s tests -v\` and \`node --check public/app.js\`.

## Recommended follow-up work (not in this PR)

- Browser-side sensitive-data preview/sanitization *before network submission* for genuinely private logs; server redaction remains defense in depth.
- Explicit structured classification for Kubernetes, GitHub Actions, and GCP deployment errors with larger grounded fixtures.
- Calibrated accuracy benchmarks on representative non-sensitive log datasets, not just success-rate tests with mocked Gemma.
- Per-client rate limiting and request concurrency controls on public CPU VMs (the existing inference quota is global).
- Optional accessible dark/light contrast review and real viewport screenshot QA.

**Do not paste confidential production logs into the public Qwiklabs demo.** The current ephemeral project and VM are for testing and may expire. The VM is not updated by a GitHub PR merge.
