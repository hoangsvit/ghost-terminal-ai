'use strict';

const $ = id => document.getElementById(id);
const input = $('log-input');
const baseline = $('baseline-input');
const button = $('generate-btn');
const tabs = Array.from(document.querySelectorAll('.tool-tab'));
let activeTool = 'analyze';

const failingLog = [
  '$ npm run start',
  '> ghost-server@1.0.0 start',
  '> node server.js',
  '[23:58:11] Starting deployment',
  'Error: listen EADDRINUSE: address already in use :::3000',
  '    at Server.setupListenHandle (node:net:1880:16)',
  '    at listenInCluster (node:net:1941:12)',
  '  code: EADDRINUSE',
  '  port: 3000',
  'Process exited with code 1',
  '[23:58:14] Deployment failed'
].join('\n');

const previousLog = [
  '$ npm run start',
  '[23:55:00] Starting deployment',
  '[23:55:02] Server listening on port 3000',
  '[23:55:03] Health check passed',
  '[23:55:04] Deployment succeeded'
].join('\n');

const storyLog = [
  '$ git status --short',
  ' M src/last-light.js',
  '?? notes/remember-me.txt',
  '$ git log --oneline -5',
  '7e4a92b fix: restore the last light in the server room',
  '0db7ee3 refactor: remove legacy heartbeat monitor',
  'b12b2a8 docs: "we will come back to this someday"',
  '$ tail -n 3 logs/worker.log',
  '[23:58:57] worker-07: heartbeat missed',
  '[23:59:03] worker-07: reconnecting...',
  '[00:00:00] worker-07: welcome back'
].join('\n');

function updateCount() {
  $('char-count').textContent = input.value.length + ' / 6000';
  $('baseline-count').textContent = baseline.value.length + ' / 6000';
}
input.addEventListener('input', updateCount);
baseline.addEventListener('input', updateCount);

$('sample-btn').addEventListener('click', () => {
  input.value = activeTool === 'story' ? storyLog : failingLog;
  if (activeTool === 'compare') baseline.value = previousLog;
  updateCount();
});

function resetResults() {
  $('empty-state').hidden = false;
  $('analysis-result').hidden = true;
  $('story-result').hidden = true;
  $('error-message').hidden = true;
}

function setTool(tool) {
  if (!['analyze', 'compare', 'story'].includes(tool) || button.disabled) return;
  activeTool = tool;
  for (const tab of tabs) {
    const selected = tab.dataset.tool === tool;
    tab.classList.toggle('active', selected);
    tab.setAttribute('aria-pressed', String(selected));
  }
  $('baseline-panel').hidden = tool !== 'compare';
  $('story-modes').hidden = tool !== 'story';
  $('tool-hint').textContent = ({
    analyze: 'Understand a failure, inspect source evidence, and decide what to verify next.',
    compare: 'Compare the previous and current runs to spot changes and new error signals.',
    story: 'Turn forgotten logs into original fiction with open-weight Gemma 3.'
  })[tool];
  $('current-label').textContent = tool === 'story' ? 'TERMINAL ARTIFACT' : (tool === 'compare' ? 'CURRENT / NEW LOG' : 'ERROR / DEPLOYMENT LOG');
  $('editor-filename').textContent = tool === 'story' ? '~/forgotten-commands.log' : '~/deployment.log';
  $('generate-label').textContent = ({
    analyze: 'Analyze logs', compare: 'Compare runs', story: 'Awaken the terminal'
  })[tool];
  resetResults();
}

for (const tab of tabs) tab.addEventListener('click', () => setTool(tab.dataset.tool));
setTool('analyze');

async function health() {
  try {
    const r = await fetch('/api/health', {cache:'no-store'});
    const d = await r.json();
    $('model-status').textContent = d.ready
      ? (d.deployment === 'vm' ? 'CLOUD GEMMA 3 READY' : 'LOCAL MODEL READY')
      : d.message;
    $('status-dot').className = d.ready ? 'ready' : 'offline';
  } catch (_) {
    $('model-status').textContent = 'MODEL STATUS UNAVAILABLE';
    $('status-dot').className = 'offline';
  }
}
health();

function error(message) {
  $('error-message').hidden = false;
  $('error-message').textContent = message;
}

function putItems(container, entries, kind) {
  const element = $(container);
  element.replaceChildren();
  if (!entries || !entries.length) {
    const p = document.createElement('p');
    p.className = 'no-evidence';
    p.textContent = kind === 'evidence'
      ? 'No known error signature detected. This does not prove the system is healthy.'
      : 'No changed lines.';
    element.appendChild(p);
    return;
  }
  for (const item of entries) {
    const row = document.createElement('div');
    row.className = kind === 'evidence' ? 'evidence-item' : 'diff-item';
    const line = document.createElement('code');
    line.textContent = 'L' + item.line + '  ' + item.text;
    row.appendChild(line);
    if (item.label) {
      const label = document.createElement('small');
      label.textContent = item.label;
      row.appendChild(label);
    }
    element.appendChild(row);
  }
}

function showDiagnosis(data) {
  $('empty-state').hidden = true;
  $('story-result').hidden = true;
  $('analysis-result').hidden = false;
  $('analysis-mode').textContent = data.mode === 'compare' ? '[ COMPARE ]' : '[ ANALYZE ]';
  $('analysis-title').textContent = data.mode === 'compare' ? 'Deployment comparison' : 'Log diagnosis';
  $('analysis-summary').textContent = data.analysis.summary;
  $('analysis-cause').textContent = data.analysis.probable_cause;
  $('severity-chip').textContent = (data.signals.severity || 'info').toUpperCase();
  $('severity-chip').dataset.severity = data.signals.severity;
  $('signals-count').textContent = data.signals.signals_found + ' SIGNAL(S)';
  putItems('evidence-list', data.signals.evidence, 'evidence');
  $('analysis-checks').replaceChildren();
  for (const step of data.analysis.checks || []) {
    const item = document.createElement('li');
    item.textContent = step;
    $('analysis-checks').appendChild(item);
  }
  $('diff-section').hidden = !data.diff;
  if (data.diff) {
    $('diff-counts').textContent = data.diff.added_count + ' line(s) added · ' +
      data.diff.removed_count + ' line(s) removed';
    putItems('diff-added', data.diff.added, 'diff');
    putItems('diff-removed', data.diff.removed, 'diff');
  }
  $('report-note').textContent = 'Confidence: ' + data.analysis.confidence.toUpperCase() +
    ' · ' + data.analysis.confidence_note +
    ' This is an AI hypothesis, not a verified incident root cause. Review steps before use.';
  $('analysis-redactions').textContent = data.redactions
    ? data.redactions + ' sensitive fragment(s) redacted'
    : 'No obvious secrets detected';
}

function showStory(data) {
  $('empty-state').hidden = true;
  $('analysis-result').hidden = true;
  $('story-result').hidden = false;
  $('story-title').textContent = data.story.title;
  $('story-body').textContent = data.story.transmission;
  $('story-whisper').textContent = '“' + data.story.whisper + '”';
  $('story-mode').textContent = '[ ' + data.mode.toUpperCase() + ' ]';
  $('redaction-count').textContent = data.redactions
    ? data.redactions + ' sensitive fragment(s) redacted'
    : 'No obvious secrets detected';
  const echoes = $('story-echoes');
  echoes.replaceChildren();
  for (const echo of data.story.echoes || []) {
    const item = document.createElement('div');
    item.className = 'echo-item';
    const fragment = document.createElement('code');
    fragment.textContent = echo.fragment;
    const meaning = document.createElement('div');
    meaning.textContent = echo.meaning;
    item.append(fragment, meaning);
    echoes.append(item);
  }
  $('echoes-block').hidden = !(data.story.echoes || []).length;
}

button.addEventListener('click', async () => {
  $('error-message').hidden = true;
  if (!input.value.trim()) {
    error('Paste a log or select “Load example” first.');
    input.focus();
    return;
  }
  if (activeTool === 'compare' && !baseline.value.trim()) {
    error('Paste the previous log or use “Load example” to fill both logs.');
    baseline.focus();
    return;
  }
  const selectedTool = activeTool;
  const path = ({analyze:'/api/analyze',compare:'/api/compare',story:'/api/interpret'})[selectedTool];
  const payload = {log:input.value};
  if (selectedTool === 'compare') payload.baseline = baseline.value;
  if (selectedTool === 'story') payload.mode = document.querySelector('input[name="mode"]:checked').value;
  button.disabled = true;
  $('generate-label').textContent = 'Inspecting the evidence…';
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 270000);
    let response;
    try {
      response = await fetch(path, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload),
        signal: controller.signal
      });
    } finally { clearTimeout(timeout); }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'AI inference failed.');
    if (selectedTool === 'story') showStory(data);
    else showDiagnosis(data);
    health();
  } catch (err) {
    error(err.name === 'AbortError' ? 'Gemma timed out. Try a shorter log.' : err.message);
  } finally {
    button.disabled = false;
    $('generate-label').textContent = ({
      analyze:'Analyze logs',compare:'Compare runs',story:'Awaken the terminal'
    })[activeTool];
  }
});

async function copyText(text, target) {
  try {
    await navigator.clipboard.writeText(text);
    target.textContent = '✓ Copied';
    setTimeout(() => { target.textContent = target.id === 'copy-btn' ? '⧉ Copy story' : '⧉ Copy report'; }, 2000);
  } catch (_) {
    error('Clipboard unavailable. Select and copy the text instead.');
  }
}
$('copy-btn').addEventListener('click', () => copyText([
  $('story-title').textContent,
  $('story-body').textContent,
  $('story-whisper').textContent,
  'Ghost Terminal AI — open-weight Gemma 3 via Ollama.'
].join('\n\n'), $('copy-btn')));

$('copy-report-btn').addEventListener('click', () => copyText([
  'Ghost Terminal AI — diagnostic report',
  $('analysis-summary').textContent,
  'Probable cause: ' + $('analysis-cause').textContent,
  'Evidence:\n' + Array.from($('evidence-list').querySelectorAll('.evidence-item code')).map(e => e.textContent).join('\n'),
  'Verification:\n' + Array.from($('analysis-checks').children).map((e, i) => (i + 1) + '. ' + e.textContent).join('\n'),
  $('report-note').textContent
].join('\n\n'), $('copy-report-btn')));
