'use strict';
const sample = [
  '$ git status --short',
  ' M src/last-light.js',
  '?? notes/remember-me.txt',
  '$ git log --oneline -5',
  '7e4a92b fix: restore the last light in the server room',
  '0db7ee3 refactor: remove legacy heartbeat monitor',
  'b12b2a8 docs: "we\'ll come back to this someday"',
  '0f00baa feat: remember old friends',
  '$ npm run build',
  '> build complete in 13.4s',
  '$ tail -n 3 logs/worker.log',
  '[23:58:57] worker-07: heartbeat missed',
  '[23:59:03] worker-07: reconnecting...',
  '[00:00:00] worker-07: welcome back'
].join('\n');
const $ = id => document.getElementById(id);
const input = $('log-input');
const button = $('generate-btn');
const updateCount = () => { $('char-count').textContent = input.value.length + ' / 6000'; };
input.addEventListener('input', updateCount);
$('sample-btn').addEventListener('click', () => { input.value = sample; updateCount(); input.focus(); });

async function health() {
  try {
    const r = await fetch('/api/health');
    const d = await r.json();
    $('model-status').textContent = d.ready
      ? (d.deployment === 'cloudrun' ? 'CLOUD GEMMA 3 READY' : 'LOCAL MODEL READY')
      : d.message;
    $('status-dot').className = d.ready ? 'ready' : 'offline';
  } catch (_) {
    $('model-status').textContent = 'LOCAL SERVER OFFLINE';
    $('status-dot').className = 'offline';
  }
}
health();

function error(message) {
  $('error-message').hidden = false;
  $('error-message').textContent = message;
}
function showStory(data) {
  $('empty-state').hidden = true;
  $('story-result').hidden = false;
  $('story-title').textContent = data.story.title;
  $('story-body').textContent = data.story.transmission;
  $('story-whisper').textContent = '“' + data.story.whisper + '”';
  $('story-mode').textContent = '[ ' + data.mode.toUpperCase() + ' ]';
  $('redaction-count').textContent = data.redactions ? data.redactions + ' sensitive fragment(s) redacted' : 'No obvious secrets detected';
  const echoes = $('story-echoes');
  echoes.replaceChildren();
  for (const echo of data.story.echoes || []) {
    const item = document.createElement('div'); item.className = 'echo-item';
    const fragment = document.createElement('code'); fragment.textContent = echo.fragment;
    const meaning = document.createElement('div'); meaning.textContent = echo.meaning;
    item.append(fragment, meaning); echoes.append(item);
  }
  $('echoes-block').hidden = !(data.story.echoes || []).length;
}
button.addEventListener('click', async () => {
  $('error-message').hidden = true;
  if (!input.value.trim()) { error('Paste a log or select “Load sample log” first.'); input.focus(); return; }
  const mode = document.querySelector('input[name="mode"]:checked').value;
  button.disabled = true;
  button.querySelector('span:nth-child(2)').textContent = 'Listening between the lines…';
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 270000);
    let response;
    try {
      response = await fetch('/api/interpret', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ log: input.value, mode }),
        signal: controller.signal
      });
    } finally { clearTimeout(timeout); }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Generation failed.');
    showStory(data); health();
  } catch (err) {
    error(err.name === 'AbortError' ? 'The model took too long. Try a smaller log or model.' : err.message);
  } finally {
    button.disabled = false;
    button.querySelector('span:nth-child(2)').textContent = 'Awaken the terminal';
  }
});
$('copy-btn').addEventListener('click', async () => {
  const story = [
    $('story-title').textContent,
    $('story-body').textContent,
    $('story-whisper').textContent,
    'Made with Ghost Terminal AI (Gemma 3, local inference).'
  ].join('\n\n');
  try {
    await navigator.clipboard.writeText(story);
    $('copy-btn').textContent = '✓ Copied';
    setTimeout(() => $('copy-btn').textContent = '⧉ Copy story', 2000);
  } catch (_) {
    error('Clipboard access failed. Please select and copy the text instead.');
  }
});
