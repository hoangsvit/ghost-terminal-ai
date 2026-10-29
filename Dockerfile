# CPU-only Google Cloud Run deployment. Model weights are baked into the image
# so scale-to-zero and cold starts do not re-download them.
FROM ollama/ollama:latest

ENV DEBIAN_FRONTEND=noninteractive \
    OLLAMA_HOST=127.0.0.1:11434 \
    OLLAMA_MODELS=/models \
    OLLAMA_NUM_PARALLEL=1 \
    OLLAMA_MAX_LOADED_MODELS=1 \
    GHOST_MODEL=gemma3:1b \
    GHOST_DEPLOYMENT=cloudrun \
    GHOST_INFERENCE_TIMEOUT=240 \
    GHOST_RATE_LIMIT_PER_MINUTE=4 \
    GHOST_HOST=0.0.0.0 \
    PORT=8080

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app.py /app/app.py
COPY ghost_terminal/ /app/ghost_terminal/
COPY public/ /app/public/
COPY cloudrun/start.sh /app/cloudrun/start.sh
RUN chmod +x /app/cloudrun/start.sh

# Validate the model download at build time; a failed pull fails the build.
# Ollama runs on loopback at build time as well as at runtime.
RUN set -eu; \
    mkdir -p /models; \
    ollama serve >/tmp/ollama-build.log 2>&1 & \
    server_pid=$!; \
    trap 'kill "$server_pid" 2>/dev/null || true' EXIT; \
    ready=0; \
    for i in $(seq 1 60); do \
      if ollama list >/dev/null 2>&1; then ready=1; break; fi; \
      sleep 2; \
    done; \
    if [ "$ready" -ne 1 ]; then cat /tmp/ollama-build.log; exit 1; fi; \
    ollama pull gemma3:1b; \
    ollama list | grep -F 'gemma3:1b'

EXPOSE 8080
ENTRYPOINT ["/app/cloudrun/start.sh"]
