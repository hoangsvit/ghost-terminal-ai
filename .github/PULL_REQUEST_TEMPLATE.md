## Summary

<!-- What changed, why, and who benefits? Link relevant issue with Fixes #NN when applicable. -->

## Scope and compatibility

<!-- List changed components/API behavior, backward compatibility, and anything intentionally out of scope. -->

## Verification

- [ ] `python3 -m unittest discover -s tests -v`
- [ ] `python3 -m compileall -q app.py ghost_terminal`
- [ ] `node --check public/app.js` and `node --test tests/test_scenarios.cjs`
- [ ] `bash -n vm/deploy.sh vm/startup.sh vm/update.sh` if deployment scripts changed
- [ ] New/changed behavior has meaningful regression tests
- [ ] Documentation updated (or not applicable)

## Safety, privacy and model behavior

- [ ] No credentials, personal data or unredacted production logs in code, screenshots or comments
- [ ] User-supplied logs remain data, never executable commands
- [ ] Evidence lines are grounded in source; AI hypotheses are not presented as verified facts
- [ ] Data flow/security impact considered if routes, prompts or hosting change

## UI / AI testing (if applicable)

<!-- Screenshots on desktop/mobile; keyboard/accessibility notes; model name and real-test result.
Do not mistake mocked CI inference for a live-model validation. -->

## Deployment

- [ ] This PR does not perform a production/public VM deployment
- [ ] If a separate deployment is required, document explicit steps and rollback

<!-- A maintainer will review before merging. Do not include sensitive security disclosures here; see SECURITY.md. -->
