'use strict';

// Synthetic examples only. Never embed real customer data, tokens, or credentials.
// These examples are explanations for testing, not guaranteed model answers.
const TEST_SCENARIOS = Object.freeze({
  analyze: [
    {
      id: 'port-conflict',
      label: 'Port conflict — EADDRINUSE',
      description: 'Node.js deployment cannot bind port 3000.',
      expected: 'HIGH severity · EADDRINUSE at line 5 · suggest checking the existing listener.',
      severity: 'high', token: 'EADDRINUSE', line: 5,
      log: [
        '$ npm run start',
        '> ghost-server@1.0.0 start',
        '> node server.js',
        '[23:58:11] Starting deployment',
        'Error: listen EADDRINUSE: address already in use :::3000',
        '    at Server.setupListenHandle (node:net:1880:16)',
        '  code: EADDRINUSE',
        '  port: 3000',
        'Process exited with code 1',
        '[23:58:14] Deployment failed'
      ].join('\n')
    },
    {
      id: 'missing-module',
      label: 'Python — missing module',
      description: 'App cannot start after a package import.',
      expected: 'MEDIUM severity · ModuleNotFoundError at line 3 · check dependencies.',
      severity: 'medium', token: 'ModuleNotFoundError', line: 3,
      log: [
        '$ python3 app.py',
        'Traceback (most recent call last):',
        "ModuleNotFoundError: No module named 'fastapi'",
        'Process exited with code 1'
      ].join('\n')
    },
    {
      id: 'out-of-memory',
      label: 'Container — out of memory',
      description: 'A container is killed while loading its model.',
      expected: 'HIGH severity · OOMKilled at line 3 · inspect resource limits.',
      severity: 'high', token: 'OOMKilled', line: 3,
      log: [
        '[02:14:06] Starting model runner',
        '[02:14:08] Loading weights...',
        'Container state: OOMKilled',
        'Process exited with code 137'
      ].join('\n')
    },
    {
      id: 'disk-full',
      label: 'Disk full — ENOSPC',
      description: 'Build cannot write an artifact to disk.',
      expected: 'HIGH severity · ENOSPC at line 3 · check free disk space.',
      severity: 'high', token: 'ENOSPC', line: 3,
      log: [
        '[12:00:00] Packing build artifacts',
        '[12:00:04] Writing /tmp/cache.tar',
        'ERROR: ENOSPC: no space left on device',
        '[12:00:05] Build failed'
      ].join('\n')
    },
    {
      id: 'region-policy',
      label: 'Google Cloud — region restricted',
      description: 'Organization policy rejects a Cloud Run region.',
      expected: 'MEDIUM severity · resourceLocations at line 3 · inspect allowed regions.',
      severity: 'medium', token: 'constraints/gcp.resourceLocations', line: 3,
      log: [
        '$ gcloud run deploy ghost-terminal-ai --region asia-southeast1',
        'FAILED_PRECONDITION: Deployment failed',
        'Constraint constraints/gcp.resourceLocations violated',
        'Project organization policy restricts this region'
      ].join('\n')
    },
    {
      id: 'connection-refused',
      label: 'Network — connection refused',
      description: 'A service cannot connect to its database.',
      expected: 'MEDIUM severity · ECONNREFUSED at line 3 · check target service.',
      severity: 'medium', token: 'ECONNREFUSED', line: 3,
      log: [
        '[08:12:30] API server booting',
        '[08:12:31] Connecting to database at 127.0.0.1:5432',
        'ERROR: connect ECONNREFUSED 127.0.0.1:5432',
        '[08:12:35] Startup incomplete'
      ].join('\n')
    },
    {
      id: 'redaction',
      label: 'Security — redaction check',
      description: 'Verify obvious credentials are hidden before analysis.',
      expected: 'MEDIUM severity · authentication failed at line 3 · 1 secret redacted.',
      severity: 'medium', token: 'authentication failed', line: 3, redactions: 1,
      log: [
        '[10:00:00] App authentication started',
        'password=synthetic-demo-only',
        'ERROR: authentication failed for service account',
        '[10:00:02] Request rejected'
      ].join('\n')
    },
    {
      id: 'no-error',
      label: 'No obvious error — uncertainty',
      description: 'Confirm that a clean-looking log is not automatically diagnosed as broken.',
      expected: 'INFO severity · no known error evidence · uncertainty remains.',
      severity: 'info', token: null, line: null,
      log: [
        '[09:30:00] Starting worker',
        '[09:30:01] Listening on port 3000',
        '[09:30:04] Health check passed'
      ].join('\n')
    }
  ],
  compare: [
    {
      id: 'deploy-regression',
      label: 'Deployment — success to failure',
      description: 'Compare a healthy deployment with one that cannot start.',
      expected: 'HIGH severity · EADDRINUSE added · previous success lines removed.',
      severity: 'high', token: 'EADDRINUSE',
      baseline: [
        '$ npm run start',
        '[23:55:00] Starting deployment',
        '[23:55:02] Server listening on port 3000',
        '[23:55:03] Health check passed',
        '[23:55:04] Deployment succeeded'
      ].join('\n'),
      log: [
        '$ npm run start',
        '[23:58:11] Starting deployment',
        'Error: listen EADDRINUSE: address already in use :::3000',
        'Process exited with code 1',
        '[23:58:14] Deployment failed'
      ].join('\n')
    },
    {
      id: 'new-import-error',
      label: 'Python — regression after update',
      description: 'A previously healthy Python startup now fails on an import.',
      expected: 'MEDIUM severity · ModuleNotFoundError added in current run.',
      severity: 'medium', token: 'ModuleNotFoundError',
      baseline: ['[12:00:00] Starting API','[12:00:01] Routes registered','[12:00:02] Listening on port 8080'].join('\n'),
      log: ['[12:03:00] Starting API','ModuleNotFoundError: No module named pydantic','Process exited with code 1'].join('\n')
    },
    {
      id: 'same-log',
      label: 'Identical logs — no changes',
      description: 'Test that Compare reports zero changes and avoids inventing a regression.',
      expected: 'INFO severity · 0 lines added · 0 removed · no new error signals.',
      severity: 'info', token: null, baseline: '[09:30:00] Worker started\n[09:30:03] Ready',
      log: '[09:30:00] Worker started\n[09:30:03] Ready',
      identical: true
    }
  ],
  story: [
    {
      id: 'midnight',
      label: 'Midnight server — haunting',
      description: 'A fictional midnight heartbeat becomes a creative short story.',
      expected: 'A generated title, transmission, whisper, and grounded echoes.',
      log: [
        '$ git status --short',
        ' M src/last-light.js',
        '?? notes/remember-me.txt',
        '$ git log --oneline -5',
        '7e4a92b fix: restore the last light in the server room',
        '0db7ee3 refactor: remove legacy heartbeat monitor',
        '[23:58:57] worker-07: heartbeat missed',
        '[23:59:03] worker-07: reconnecting...',
        '[00:00:00] worker-07: welcome back'
      ].join('\n')
    },
    {
      id: 'forgotten-feature',
      label: 'Forgotten feature — remembrance',
      description: 'Git history suggests a gentle story about unfinished work.',
      expected: 'A new story inspired by real sample excerpts, not an error diagnosis.',
      log: [
        '$ git log --oneline -4',
        'a102bc3 feat: save unfinished notes',
        'c5b849a refactor: archive the first prototype',
        'e99de10 docs: we will return to this idea',
        '1aa2390 fix: make the old dashboard open again',
        '$ git status --short',
        ' M memories/notes.md'
      ].join('\n')
    }
  ]
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = TEST_SCENARIOS;
}
