# Repository maintenance guide

This document describes the maintainers' operating process. It does **not** claim repository settings have already been enabled.

## Community entry points

- [README](../README.md) — what the project does and how to run it.
- [CONTRIBUTING](../CONTRIBUTING.md) — fork, code standards, checks, PR review.
- [Issue forms](../.github/ISSUE_TEMPLATE) — bug, feature, docs, question.
- [PR template](../.github/PULL_REQUEST_TEMPLATE.md) — evidence and safety checklist.
- [Code of Conduct](../CODE_OF_CONDUCT.md) — community conduct and enforcement.
- [Security policy](../SECURITY.md) — private reporting and threat model.
- [Support](../SUPPORT.md) — reproducible, privacy-conscious help requests.
- [MIT License](../LICENSE) — rights to this repository's source (not the Gemma/Ollama distributions).

## Issue lifecycle

1. **Intake:** read templates; request a minimal synthetic reproduction if missing.
2. **Triage:** distinguish defect, feature, documentation and security. **Never ask contributors to post private logs.**
3. **Prioritize:** prioritize safety/privacy, grounded diagnoses, regressions and deployment reliability ahead of cosmetic changes.
4. **Assign or invite contributions:** describe acceptance criteria, affected modules and a suitable test plan; avoid duplicate issues.
5. **Review PR:** check CI and changes against the issue; request targeted improvements if necessary.
6. **Close:** cross-link the merged PR and confirm the resolution; reopen if evidence shows the issue remains.

### Suggested labels to create in GitHub Settings

GitHub issue forms here deliberately do not require labels that may not exist yet. Maintainers can create labels separately in **Issues → Labels**, then assign them during triage:

| Label | Purpose |
| --- | --- |
| `type: bug` | Reproducible defect |
| `type: feature` | Improvement proposal |
| `type: docs` | Documentation task |
| `type: question` | Usage/support question |
| `priority: high` | Security, data-safety or blocking regression |
| `priority: medium` | Important quality/operability improvement |
| `priority: low` | Nice-to-have |
| `good first issue` | Bounded beginner-friendly task with test guidance |
| `help wanted` | Maintainer-approved external contribution |
| `needs reproduction` | Lacks steps or synthetic fixture |
| `blocked` | Waiting on another change or external condition |

Do not pre-assign speculative milestones or create a large issue backlog without acceptance criteria.

## Suggested repository settings (manual GitHub owner action)

The YAML/files in this PR **cannot** enforce repository settings by themselves. Review these settings manually:

- **Settings → General:** Issues enabled; wiki/discussions optional only if someone will maintain them.
- **Settings → Branches / Rulesets:** protect `main`, require relevant CI (currently job named `test` in workflow `Python CI`), block force pushes, require reviewed PRs and up-to-date checks as appropriate for contributor capacity. Do not grant bypass broadly.
- **Settings → Actions → General:** use least-privilege token permissions and avoid untrusted PR code with write credentials.
- **CI events:** run automatically for PRs and `main` pushes; contributors can request a manual `workflow_dispatch` run from the Actions tab. PR updates cancel outdated runs to reduce CI duplication.
- **Security / Advanced Security:** consider enabling private vulnerability reporting, dependency alerts, and supported scanning features. `SECURITY.md` by itself does not enable private reporting.
- **Maintain proper ownership:** no CODEOWNERS is added yet because reviewer assignments need the repository owner's approval.

## Contribution and CI policy

- Small changes: focused PR and meaningful tests.
- Changes to parser/rules: synthetic fixture of positive and negative examples; never let AI invent citations.
- Changes to model prompts: mock-schema tests plus explicitly identified manual Gemma results.
- Changes to UI: keyboard/mobile checks and screenshots; avoid inserting raw HTML from untrusted sources.
- Changes to deployment: syntax tests, fail-safe behavior and rollback path; **never auto-deploy public VM from PR workflows**.
- Dependency update PRs: review license, supply chain, compatibility and CI; Dependabot opens PRs but **never auto-merges** them.

## Release and deployment policy

1. Merge an approved, passing PR into `main`; this is a source-code action, not a server rollout.
2. Record user-visible changes, security notes and breaking changes in release notes. Tags can follow `vMAJOR.MINOR.PATCH` when releases are warranted.
3. For a public VM deploy, obtain explicit approval and use `vm/update.sh --ref main` with a known project and zone. Monitor actual application behavior.
4. If the updated version is unhealthy, use `vm/update.sh --rollback` and report the regression as an issue.
5. Qwiklabs/temporary VMs may expire; never represent ephemeral demo hosting as permanent production infrastructure.

## Project health checklist

At regular intervals, review issue responsiveness, open/closed PRs, CI reliability, Dependabot changes, exposed secrets, stale links, accessibility, docs accuracy and any costs from persistent cloud infrastructure.

This guide is intentionally lightweight and can evolve through community PRs.
