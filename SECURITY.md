# Security Policy

## Supported versions

| Version | Security maintenance |
| --- | --- |
| Current `main` | Best-effort security fixes |
| Older commits, archived branches and ephemeral VM demos | Not independently maintained |

This is a volunteer open-source project. There is no guaranteed SLA, security audit or warranty.

## Report a vulnerability privately

**Do not open a public issue or PR with exploit details, tokens, passwords, private logs, or personal data.**

1. Check whether this repository has **Private vulnerability reporting** enabled under its GitHub **Security** tab.
2. If available, use GitHub's private vulnerability report flow. If that feature is not enabled, seek a private contact channel with the repository maintainer instead of publicly disclosing details.
3. Include a minimal synthetic reproduction, affected version/commit, impact and recommended remediation. Do not send real customer data.
4. Allow maintainers a reasonable opportunity to assess and coordinate a fix before public disclosure. Response times are not guaranteed.

Repository maintainers may configure GitHub private vulnerability reporting in **Settings → Security / Advanced Security**; this file alone does not enable it.

## Threat model and limitations

- Hosted demos process user-submitted logs **on the server**. Browser-to-server transport sends the original input before server-side best-effort redaction. Never upload confidential logs to a public demo.
- Redaction catches common token and password patterns but is **not a guarantee**. Review inputs before sharing reports or opening issues.
- Ollama is bound to loopback by default. Do not expose its API directly to the internet.
- Logs and AI output are untrusted. Prompts can be manipulated by input data; model recommendations are hypotheses, not guaranteed safe instructions.
- The app must never execute pasted commands or automatically apply suggested fixes.
- The public Compute Engine example has demo-oriented rate limiting, not a production authentication, multi-tenant isolation, or hard-cost-control system.
- The sample VM in Qwiklabs is **temporary**; hosted availability and public URLs are not guaranteed.

## Security-related changes

Security fixes should include regression tests, minimal necessary disclosure in the public changelog, and a review of data flow and error messages. See [CONTRIBUTING.md](CONTRIBUTING.md) for development standards.
