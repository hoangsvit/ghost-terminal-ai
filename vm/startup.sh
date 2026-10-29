#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
# GCE startup scripts run without a login environment; Ollama CLI requires HOME.
export HOME="${HOME:-/root}"
mkdir -p "$HOME"

exec > >(tee -a /var/log/ghost-terminal-bootstrap.log) 2>&1
trap 'echo "ERROR: bootstrap failed; see /var/log/ghost-terminal-bootstrap.log" >&2' ERR
APP_DIR=/opt/ghost-terminal-ai
STATE_DIR=/var/lib/ghost-terminal-ai
echo "===== ePlus.DEV - Starting Execution | Ghost Terminal VM ====="
mkdir -p "$STATE_DIR"
if [[ ! -f "$STATE_DIR/installed" ]]; then
  echo "[1/5] Install Ubuntu packages"
  apt-get update -qq
  if ! apt-get install -y --no-install-recommends ca-certificates curl git python3 caddy; then
    apt-get install -y software-properties-common
    add-apt-repository -y universe
    apt-get update -qq
    apt-get install -y --no-install-recommends ca-certificates curl git python3 caddy
  fi
  echo "[2/5] Install Ollama and enforce loopback binding"
  curl -fsSL --retry 3 https://ollama.com/install.sh -o /tmp/ollama-install.sh
  sh /tmp/ollama-install.sh
  mkdir -p /etc/systemd/system/ollama.service.d
  cat > /etc/systemd/system/ollama.service.d/override.conf <<'EOF'
[Service]
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
EOF
  systemctl daemon-reload
  systemctl enable --now ollama
  systemctl restart ollama
  echo "[3/5] Clone VM branch from GitHub"
  if ! id ghostapp >/dev/null 2>&1; then
    useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin ghostapp
  fi
  if [[ ! -d "$APP_DIR/.git" ]]; then
    git clone --depth=1 --branch=main https://github.com/hoangsvit/ghost-terminal-ai.git "$APP_DIR"
  fi
  chown -R ghostapp:ghostapp "$APP_DIR"
  echo "[4/5] Download Gemma 3 1B once to VM persistent disk"
  for i in {1..30}; do
    if curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null; then break; fi
    sleep 2
  done
  ollama pull gemma3:1b
  ollama list | grep -Fq 'gemma3:1b'
  cat > /etc/systemd/system/ghost-terminal.service <<'EOF'
[Unit]
Description=Ghost Terminal AI — Gemma 3 on Compute Engine
After=network-online.target ollama.service
Requires=ollama.service
Wants=network-online.target

[Service]
Type=simple
User=ghostapp
Group=ghostapp
WorkingDirectory=/opt/ghost-terminal-ai
Environment=GHOST_HOST=127.0.0.1
Environment=GHOST_PORT=8765
Environment=GHOST_MODEL=gemma3:1b
Environment=GHOST_DEPLOYMENT=vm
Environment=GHOST_INFERENCE_TIMEOUT=240
Environment=GHOST_RATE_LIMIT_PER_MINUTE=3
ExecStart=/usr/bin/python3 /opt/ghost-terminal-ai/app.py
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable --now ghost-terminal
  touch "$STATE_DIR/installed"
else
  echo "[1-4/5] Previous install found; keep model, restart services"
  systemctl enable --now ollama
  systemctl enable --now ghost-terminal
fi
echo "[5/5] Set up automatic HTTPS with Caddy"
META=http://metadata.google.internal/computeMetadata/v1
IP="$(curl -fsS --retry 5 --retry-delay 2 -H 'Metadata-Flavor: Google' "$META/instance/network-interfaces/0/access-configs/0/external-ip")"
[[ -n "$IP" ]] || { echo 'VM has no external IPv4 address' >&2; exit 1; }
DOMAIN="$IP.sslip.io"
cat > /etc/caddy/Caddyfile <<EOF
$DOMAIN {
    encode gzip
    header {
        X-Content-Type-Options nosniff
        Referrer-Policy no-referrer
        X-Frame-Options DENY
    }
    reverse_proxy 127.0.0.1:8765 {
        transport http {
            read_timeout 300s
        }
    }
}
EOF
caddy validate --config /etc/caddy/Caddyfile
systemctl enable --now caddy
systemctl restart caddy
echo "==== VM APP CONFIGURED ===="
echo "Candidate URL: https://$DOMAIN"
echo "HTTPS depends on public DNS, open ports 80/443 and certificate issuance."
echo "Local health:"
curl -fsS --max-time 10 http://127.0.0.1:8765/api/health || true
echo
echo "Logs: /var/log/ghost-terminal-bootstrap.log"
