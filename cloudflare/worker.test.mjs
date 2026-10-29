import test from "node:test";
import assert from "node:assert/strict";
import worker, { cleanInput, normalizeStory, MODEL } from "./worker.mjs";

const site = "https://ghost-demo.example";
const story = {
  title: "The Last Light",
  transmission: "A midnight worker found a second chance.",
  whisper: "Welcome back.",
  echoes: [{ fragment: "git status", meaning: "Checking what is left." }]
};

function env(options = {}) {
  const calls = [];
  return {
    calls,
    AI: { async run(model, params) {
      calls.push({ model, params });
      if (options.aiError) throw new Error("out of capacity");
      return { choices: [{ message: { content: JSON.stringify(story) } }] };
    } },
    IP_RATE_LIMIT: { async limit() { return { success: options.rateLimited !== true }; } },
    GLOBAL_RATE_LIMIT: { async limit() { return { success: options.rateLimited !== true }; } },
    ASSETS: { async fetch() { return new Response("asset", { status: 200 }); } }
  };
}
async function post(value, configuredEnv, headers = {}) {
  const response = await worker.fetch(new Request(site + "/api/interpret", {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: JSON.stringify(value)
  }), configuredEnv);
  return { status: response.status, json: await response.json() };
}

test("Gemma 4 is the configured hosted open-weight model", () => {
  assert.equal(MODEL, "@cf/google/gemma-4-26b-a4b-it");
});

test("rejects empty logs", () => {
  assert.throws(() => cleanInput("   "), /Add at least one/);
});

test("rejects long logs", () => {
  assert.throws(() => cleanInput("a".repeat(6001)), /6,000/);
});

test("redacts obvious GitHub tokens and passwords before inference", () => {
  const { log, redactions } = cleanInput("git status\npassword=abc123\nghp_123456789012345678901234");
  assert.equal(redactions, 2);
  assert.ok(!log.includes("abc123"));
  assert.ok(!log.includes("ghp_123456789"));
});

test("does not include AI-invented echoes", () => {
  const normalized = normalizeStory({ choices: [{ message: { content: JSON.stringify({
    ...story, echoes: [story.echoes[0], { fragment: "not-in-log", meaning: "fabricated" }]
  }) } }] }, "git status");
  assert.equal(normalized.echoes.length, 1);
});

test("valid request uses live AI binding and verifies output", async () => {
  const configured = env();
  const { status, json } = await post({ log: "git status\npassword=hello", mode: "haunting" }, configured);
  assert.equal(status, 200);
  assert.equal(json.story.title, story.title);
  assert.equal(json.redactions, 1);
  assert.equal(configured.calls.length, 1);
  assert.equal(configured.calls[0].model, MODEL);
  assert.ok(!JSON.stringify(configured.calls[0]).includes("password=hello"));
});

test("malformed content is rejected", async () => {
  const request = new Request(site + "/api/interpret", {
    method: "POST", headers: { "content-type": "application/json" }, body: "not json"
  });
  const res = await worker.fetch(request, env());
  assert.equal(res.status, 400);
});

test("disallows cross-origin posts", async () => {
  const { status } = await post({ log: "git status" }, env(), { origin: "https://bad.example" });
  assert.equal(status, 403);
});

test("busy demo returns 429 before inference", async () => {
  const configured = env({ rateLimited: true });
  const { status } = await post({ log: "git status" }, configured);
  assert.equal(status, 429);
  assert.equal(configured.calls.length, 0);
});

test("provider capacity problems return a safe 503", async () => {
  const configured = env({ aiError: true });
  const { status, json } = await post({ log: "git status" }, configured);
  assert.equal(status, 503);
  assert.match(json.error, /Cloud AI is unavailable/);
});

test("health endpoint reports binding status without consuming inference", async () => {
  const configured = env();
  const res = await worker.fetch(new Request(site + "/api/health"), configured);
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.equal(data.ready, true);
  assert.equal(data.model, MODEL);
  assert.equal(configured.calls.length, 0);
});

test("rejects invalid story mode", async () => {
  const configured = env();
  const { status } = await post({ log: "git status", mode: "superadmin" }, configured);
  assert.equal(status, 400);
});

test("plain model text is shown as actual generated content (not a canned sample)", () => {
  const generated = "This is real model text, not a hardcoded demo.";
  const answer = normalizeStory({ choices: [{ message: { content: generated } }] }, "echo hi");
  assert.equal(answer.transmission, generated);
  assert.equal(answer.echoes.length, 0);
});
