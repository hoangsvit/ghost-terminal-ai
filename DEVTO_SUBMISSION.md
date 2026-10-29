---
title: "Ghost Terminal AI: A Local Gemma 3 Storyteller for Forgotten Logs"
published: false
description: "Transform terminal traces into haunting stories with open-weight AI running on your own machine."
tags: devchallenge, hf26challenge, opensource, ai
---

# Ghost Terminal AI: Every Log Leaves a Haunting 👻

*Hacktoberfest 2026 — Week 4: Ghost in the Machine*

## What I Built

A local, privacy-first storytelling studio that turns forgotten command histories, CI logs, and Git commits into original microfiction.

Paste a log, pick a frequency (**Haunting**, **Remembrance**, or **Mystery**), and a locally hosted **Gemma 3** model writes a title, a short story, a final whisper, and grounded echoes from the original lines. This is not a preprogrammed output: Gemma generates the actual narrative.

The goal is to explore what an open-weight model can do with ordinary artifacts of software development—without sending potentially personal log text to a remote AI API.

## Demo

**Real model demonstration:** [ADD YOUR SCREEN RECORDING LINK BEFORE PUBLISHING]

Run the demo on your own computer:

1. Install [Ollama](https://ollama.com/download) and [Python](https://python.org/downloads/).
2. Download an open-weight model with `ollama pull gemma3:1b`.
3. Run `python app.py`.
4. Open `http://127.0.0.1:8765`, then click **Load sample log**.
5. Select **Haunting** and click **Awaken the terminal**.
6. Switch to **Remembrance** or **Mystery** and see how the same input leads to a new interpretation.

A screenshot of the static interface is not evidence of a real model run; the recording should show the model indicator and actual generated output.

## Code

**Public GitHub repository:** https://github.com/hoangsvit/ghost-terminal-ai

The source is Python standard library + vanilla HTML/CSS/JS. It does not require npm packages, pip dependencies, paid API keys, or external inference.

## How I Built It

The app contains four main layers:

- **Input validation and sanitization:** `ghost_terminal/core.py` limits input size, removes control characters, and redacts common token/password patterns before inference.
- **Local inference:** `ghost_terminal/ollama_client.py` talks only to loopback Ollama through `/api/generate` and requests structured JSON output from Gemma 3.
- **Safety checks:** returned source echoes are accepted only if the quote exists verbatim in the redacted input. The app never executes any pasted commands.
- **Story interface:** `app.py` provides a local HTTP server; the static browser UI displays output using `textContent` rather than injecting generated HTML.

The model is the core creative component. Without Ollama and the downloaded Gemma weights, generation cannot run.

I tested the HTTP server and inference transport with **19 offline tests** using a fake model response. Those tests exercise request handling, basic redaction, output validation, origin checks, and local-only transport. They do **not** claim to measure model quality or real-world latency.

The interface is built as a dark, atmospheric instrument panel. One side accepts the terminal artifact; the other waits for a fictional transmission from the model.

## Why Does Open Innovation Matter?

I like experiments that keep running after an API trial expires. Open-weight models make small, creative software projects possible without a remote service account, usage billing, or provider lock-in.

An on-device model also means the user gets to choose what material stays on their own computer. The code is readable, prompts can be customized, and different Gemma sizes can be tested without rewriting the application. It is transparent enough for a student or another developer to fork, audit, and improve.

Privacy is not a magic guarantee. Basic redaction can miss secrets, and LLM prompt injection is still a concern. That's why the README documents practical limits and asks users not to paste genuinely sensitive logs. Openness makes those limits easier to inspect.

## The Spirit of It

I started with an intentionally fictional log: a commit about restoring the last light, a worker losing its heartbeat, and a midnight line reading `welcome back`. Haunting mode reads it as a ghost story. Remembrance mode sees the people behind the system. Mystery mode asks what happened between the timestamps.

The most interesting part is not the synthetic sample—it is how a small, open-weight model can interpret technical traces differently based on a human creative direction.

## Prize Categories

**Best Use of Gemma** — Gemma 3 performs the real narrative generation locally via Ollama.

---

*Created for Hacktoberfest 2026 Week 4 (October 26–31). MIT-licensed application source. Gemma weights and Ollama use their own licenses.*

> **Before publishing:** replace the real-demo placeholder with an actual screen recording; verify all challenge tags and live submission availability on DEV.to.
