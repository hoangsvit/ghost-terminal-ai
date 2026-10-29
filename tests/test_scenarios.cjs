'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const cases = require('../public/scenarios.js');

test('tools have curated test scenarios with stable IDs', () => {
  assert.deepEqual(Object.keys(cases), ['analyze', 'compare', 'story']);
  assert.equal(cases.analyze.length, 8);
  assert.equal(cases.compare.length, 3);
  assert.equal(cases.story.length, 2);
  for (const [tool, samples] of Object.entries(cases)) {
    const ids = new Set();
    for (const item of samples) {
      assert.match(item.id, /^[a-z0-9-]+$/);
      assert.ok(!ids.has(item.id), 'duplicate scenario ' + item.id);
      ids.add(item.id);
      assert.ok(item.label && item.description && item.expected);
      assert.ok(item.log && item.log.length <= 6000);
      assert.ok(item.log.split('\n').length <= 100);
      if (tool === 'compare') {
        assert.ok(item.baseline && item.baseline.length <= 6000);
        assert.ok(item.baseline.split('\n').length <= 100);
      }
    }
  }
});

test('analyzer cases reference actual, correctly numbered log lines', () => {
  for (const item of cases.analyze) {
    if (item.token) {
      assert.ok(item.log.split('\n')[item.line - 1].includes(item.token), item.id);
    } else {
      assert.equal(item.severity, 'info');
    }
  }
});

test('compare regression cases have real introduced signatures', () => {
  for (const item of cases.compare) {
    if (item.identical) assert.equal(item.baseline, item.log);
    else {
      assert.notEqual(item.baseline, item.log);
      assert.ok(item.log.includes(item.token), item.id);
      assert.ok(!item.baseline.includes(item.token), item.id);
    }
  }
});

test('story samples are distinct and sourced from fictional Git history', () => {
  assert.notEqual(cases.story[0].log, cases.story[1].log);
  for (const item of cases.story) assert.match(item.log, /git/);
});
