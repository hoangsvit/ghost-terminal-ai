#!/usr/bin/env bash
# Starts a loopback-only Ollama instance and the public-facing Python app.
# No model downloads should occur at runtime.
set -Eeuo pipefail

export OLLAMA_HOST="127.0.0.1:11434"
export GHOST_HOST="0.0.0.0"
export GHOST_PORT="${PORT:-8080}"
export GHOST_DEPLOYMENT="cloudrun"

ollama serve &
ollama_pid=$!
web_pid=""

cleanup() {
  trap - EXIT TERM INT
  if [[ -n "$web_pid" ]]; then kill "$web_pid" 2>/dev/null || true; fi
  kill "$ollama_pid" 2>/dev/null || true
  if [[ -n "$web_pid" ]]; then wait "$web_pid" 2>/dev/null || true; fi
  wait "$ollama_pid" 2>/dev/null || true
}
trap cleanup EXIT TERM INT

echo "[ghost-terminal-ai] Waiting for local Ollama…"
ready=0
for i in {1..60}; do
  if ! kill -0 "$ollama_pid" 2>/dev/null; then
    echo "[ghost-terminal-ai] Ollama exited unexpectedly" >&2
    exit 1
  fi
  if ollama list >/dev/null 2>&1; then ready=1; break; fi
  sleep 2
done
if [[ "$ready" -ne 1 ]]; then
  echo "[ghost-terminal-ai] Ollama did not become ready" >&2
  exit 1
fi
if ! ollama list | grep -Fq "${GHOST_MODEL:-gemma3:1b}"; then
  echo "[ghost-terminal-ai] Image does not contain the requested model" >&2
  exit 1
fi

echo "[ghost-terminal-ai] Starting Python on 0.0.0.0:${GHOST_PORT}"
python3 /app/app.py &
web_pid=$!

# If either process exits, shut down the container; no orphaned Ollama process.
set +e
wait -n "$ollama_pid" "$web_pid"
status=$?
set -e
exit "$status"
