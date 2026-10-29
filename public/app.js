'use strict';

const $ = id => document.getElementById(id);
const input = $('log-input');
const baseline = $('baseline-input');
const button = $('generate-btn');
const tabs = Array.from(document.querySelectorAll('.tool-tab'));
let activeTool = 'analyze';

let loadedScenario = null;
let lastReport = null;

function selectedScenario() {
  return TEST_SCENARIOS[activeTool].find(s => s.id === $('scenario-select').value);
}

function explainScenario() {
  const scenario = selectedScenario();
  $('scenario-description').textContent = scenario ? scenario.description : '';
  $('scenario-expected').textContent = scenario ? 'Expected: ' + scenario.expected : '';
}

function populateScenarios() {
  const select = $('scenario-select');
  select.replaceChildren();
  const scenarios = TEST_SCENARIOS[activeTool];
  for (const scenario of scenarios) {
    const option = document.createElement('option');
    option.value = scenario.id;
    option.textContent = scenario.label;
    select.appendChild(option);
  }
  $('scenario-count').textContent = scenarios.length + ' examples';
  explainScenario();
}

function verifyLoadedScenario(data, tool) {
  const element = $('scenario-verification');
  element.hidden = true;
  const scenario = loadedScenario;
  if (!scenario || scenario.tool !== tool ||
      input.value !== scenario.log ||
      (tool === 'compare' && baseline.value !== scenario.baseline)) return;

  const checks = [];
  if (tool === 'story') {
    checks.push(Boolean(data.story && data.story.title && data.story.transmission && data.story.whisper));
  } else {
    const signals = data.signals || {};
    const evidence = signals.evidence || [];
    checks.push(signals.severity === scenario.severity);
    if (scenario.token) {
      checks.push(evidence.some(item =>
        item.text.includes(scenario.token) &&
        (scenario.line == null || item.line === scenario.line)));
    } else {
      checks.push((signals.signals_found || 0) === 0);
    }
    if (scenario.redactions != null) checks.push(data.redactions === scenario.redactions);
    if (tool === 'compare') {
      const diff = data.diff || {};
      if (scenario.identical) {
        checks.push(diff.added_count === 0 && diff.removed_count === 0);
      } else {
        checks.push(diff.added_count > 0 && diff.removed_count > 0);
        checks.push((diff.new_error_signals || []).some(item => item.text.includes(scenario.token)));
      }
    }
  }
  const passed = checks.filter(Boolean).length;
  element.hidden = false;
  element.dataset.result = passed === checks.length ? 'pass' : 'review';
  element.textContent = 'Sample check: ' + passed + '/' + checks.length +
    ' expected signals matched. This checks log evidence/output structure, not AI diagnosis accuracy.';
}

function updateCount() {
  $('char-count').textContent = input.value.length + ' / 6000';
  $('baseline-count').textContent = baseline.value.length + ' / 6000';
}
function onEdit() {
  updateCount();
  resetResults();
}
input.addEventListener('input', onEdit);
baseline.addEventListener('input', onEdit);
$('ignore-timestamps').addEventListener('change', () => { resetResults(); });

$('scenario-select').addEventListener('change', () => {
  loadedScenario = null;
  $('scenario-verification').hidden = true;
  explainScenario();
});

$('sample-btn').addEventListener('click', () => {
  if (button.disabled) return;
  const scenario = selectedScenario();
  if (!scenario) return;
  input.value = scenario.log;
  if (activeTool === 'compare') baseline.value = scenario.baseline;
  loadedScenario = {tool: activeTool, ...scenario};
  updateCount();
  resetResults();
  input.focus();
});

function resetResults() {
  lastReport = null;
  $('empty-state').hidden = false;
  $('analysis-result').hidden = true;
  $('story-result').hidden = true;
  $('error-message').hidden = true;
  $('scenario-verification').hidden = true;
}

function setTool(tool) {
  if (!['analyze', 'compare', 'story'].includes(tool) || button.disabled) return;
  activeTool = tool;
  loadedScenario = null;
  populateScenarios();
  for (const tab of tabs) {
    const selected = tab.dataset.tool === tool;
    tab.classList.toggle('active', selected);
    tab.setAttribute('aria-pressed', String(selected));
  }
  $('baseline-panel').hidden = tool !== 'compare';
  $('story-modes').hidden = tool !== 'story';
  $('quick-scan-btn').hidden = tool === 'story';
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
  lastReport = data;
  const isQuick = data.engine === 'rules';
  $('engine-indicator').textContent = isQuick ? 'NO AI · INSTANT' : 'GEMMA 3';
  $('analysis-source-label').textContent = isQuick ? 'RULE-BASED INDICATOR' : 'AI HYPOTHESIS';
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
      data.diff.removed_count + ' line(s) removed' +
      (data.diff.ignore_timestamps ? ' · Timestamp-only changes ignored' : '');
    putItems('diff-added', data.diff.added, 'diff');
    putItems('diff-removed', data.diff.removed, 'diff');
  }
  $('report-note').textContent = 'Source: ' + (isQuick ? 'Deterministic rules' : 'Gemma 3 AI') +
    ' · Confidence: ' + data.analysis.confidence.toUpperCase() +
    ' · ' + data.analysis.confidence_note +
    ' Findings are not a verified root cause. Review every suggested step before use.';
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
    error('Paste a log or choose a test scenario first.');
    input.focus();
    return;
  }
  if (activeTool === 'compare' && !baseline.value.trim()) {
    error('Paste the previous log or load a Compare scenario first.');
    baseline.focus();
    return;
  }
  const selectedTool = activeTool;
  const path = ({analyze:'/api/analyze',compare:'/api/compare',story:'/api/interpret'})[selectedTool];
  const payload = {log:input.value};
  if (selectedTool === 'compare') {
    payload.baseline = baseline.value;
    payload.ignore_timestamps = $('ignore-timestamps').checked;
  }
  if (selectedTool === 'story') payload.mode = document.querySelector('input[name="mode"]:checked').value;
  button.disabled = true;
  $('sample-btn').disabled = true;
  $('scenario-select').disabled = true;
  $('quick-scan-btn').disabled = true;
  input.disabled = true;
  baseline.disabled = true;
  $('ignore-timestamps').disabled = true;
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
    verifyLoadedScenario(data, selectedTool);
    health();
  } catch (err) {
    error(err.name === 'AbortError' ? 'Gemma timed out. Try a shorter log.' : err.message);
  } finally {
    button.disabled = false;
    $('sample-btn').disabled = false;
    $('scenario-select').disabled = false;
    $('quick-scan-btn').disabled = false;
    input.disabled = false;
    baseline.disabled = false;
    $('ignore-timestamps').disabled = false;
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


// The fast scan is deliberately independent of Ollama and the hosted inference throttle.
$('quick-scan-btn').addEventListener('click', async () => {
  $('error-message').hidden = true;
  if (!input.value.trim()) {
    error('Paste a log or load a scenario before scanning.');
    input.focus();
    return;
  }
  if (activeTool === 'compare' && !baseline.value.trim()) {
    error('Enter a previous log or load a Compare scenario first.');
    baseline.focus();
    return;
  }
  const tool = activeTool;
  const payload = {log:input.value};
  if (tool === 'compare') {
    payload.baseline = baseline.value;
    payload.ignore_timestamps = $('ignore-timestamps').checked;
  }
  $('quick-scan-btn').disabled = true;
  button.disabled = true;
  $('sample-btn').disabled = true;
  $('scenario-select').disabled = true;
  input.disabled = true;
  baseline.disabled = true;
  $('ignore-timestamps').disabled = true;
  try {
    const response = await fetch('/api/inspect', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Quick scan failed.');
    showDiagnosis(data);
    verifyLoadedScenario(data, tool);
  } catch (err) {
    error(err.message || 'Unable to inspect logs.');
  } finally {
    $('quick-scan-btn').disabled = false;
    button.disabled = false;
    $('sample-btn').disabled = false;
    $('scenario-select').disabled = false;
    input.disabled = false;
    baseline.disabled = false;
    $('ignore-timestamps').disabled = false;
  }
});

function markdownReport(data) {
  if (!data || !data.analysis) return '';
  const d = data.analysis;
  const result = [
    '# Ghost Terminal AI — Diagnostic Report',
    '',
    '- Tool: ' + (data.mode === 'compare' ? 'Compare Logs' : 'Analyze Logs'),
    '- Engine: ' + (data.engine === 'rules' ? 'Instant rules (no model)' : 'Gemma 3 AI'),
    '- Severity: ' + (data.signals?.severity || 'info').toUpperCase(),
    '- Confidence: ' + d.confidence + ' (not a calibrated probability)',
    '',
    '## Summary', d.summary,
    '',
    '## Possible cause (unverified)', d.probable_cause,
    '',
    '## Evidence from sanitized input'
  ];
  const evidence = data.signals?.evidence || [];
  if (evidence.length) {
    for (const e of evidence) {
      // Inline evidence lines remain plain text in a block quote, not executed commands.
      result.push('- Line ' + e.line + ' [' + e.label + ']: ' + e.text.replaceAll('\n', ' '));
    }
  } else result.push('No known error signature detected.');
  result.push('', '## Suggested checks (review before running)');
  for (const [i, check] of (d.checks || []).entries()) result.push((i + 1) + '. ' + check);
  if (data.diff) {
    result.push('', '## Before / after differences',
      '- Added: ' + data.diff.added_count,
      '- Removed: ' + data.diff.removed_count,
      '- Ignore timestamp-only changes: ' + Boolean(data.diff.ignore_timestamps),
      '',
      '### Added lines (current)');
    for (const line of data.diff.added || []) result.push('- L' + line.line + ': ' + line.text);
    result.push('', '### Removed lines (previous)');
    for (const line of data.diff.removed || []) result.push('- L' + line.line + ': ' + line.text);
  }
  result.push('', '> This is a debugging aid, not a verified root cause. '
    + 'Log excerpts were sanitized on the server using best-effort patterns. '
    + 'Review the report before sharing it.');
  return result.join('\n');
}

$('download-report-btn').addEventListener('click', () => {
  if (!lastReport) return;
  const markdown = markdownReport(lastReport);
  const url = URL.createObjectURL(new Blob([markdown], {type:'text/markdown;charset=utf-8'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'ghost-terminal-report.md';
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 3000);
});
