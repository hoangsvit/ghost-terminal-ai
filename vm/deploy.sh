#!/usr/bin/env bash
# Cloud Shell entrypoint. VM startup continues if Cloud Shell disconnects.
set -Eeuo pipefail
C_RESET=$'\033[0m'; C_GREEN=$'\033[0;32m'; C_BLUE=$'\033[0;34m'; C_YELLOW=$'\033[0;33m'
info(){ printf '%s%s%s\n' "$C_BLUE" "$*" "$C_RESET"; }
warn(){ printf '%s%s%s\n' "$C_YELLOW" "$*" "$C_RESET" >&2; }
die(){ echo "ERROR: $*" >&2; exit 1; }
printf '%s\n' "${C_GREEN}ePlus.DEV - Starting Execution${C_RESET}"
info "Ghost Terminal AI | Google Compute Engine VM"
for tool in gcloud git curl; do command -v "$tool" >/dev/null || die "Missing command: $tool"; done
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
[[ -n "$PROJECT_ID" && "$PROJECT_ID" != "(unset)" ]] || die "No project selected"
VM_NAME="${VM_NAME:-ghost-terminal-ai-vm}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-standard-2}"
NETWORK="${NETWORK:-default}"
FIREWALL_RULE="${FIREWALL_RULE:-ghost-terminal-ai-web}"
TAG=ghost-terminal-ai-web
STARTUP="$(mktemp /tmp/ghost-vm-startup.XXXXXXXX.sh)"
LOG="$(mktemp /tmp/ghost-vm-create.XXXXXXXX.log)"
trap 'rm -f "$STARTUP" "$LOG"' EXIT
info "[1/6] Project: $PROJECT_ID, machine: $MACHINE_TYPE"
if [[ "$PROJECT_ID" == qwiklabs-* ]]; then
  warn "Temporary Qwiklabs project detected. This VM and URL may expire with the lab."
fi
warn "Compute Engine VM, disk and public IP may incur charges until stopped/deleted."
gcloud services enable compute.googleapis.com --project="$PROJECT_ID" --quiet
info "[2/6] Fetching startup script"
curl -fsSL --retry 3 \
  'https://raw.githubusercontent.com/hoangsvit/ghost-terminal-ai/feature/compute-engine-vm-gemma3/vm/startup.sh' \
  -o "$STARTUP" || die "Failed to download startup script"
bash -n "$STARTUP" || die "Startup script failed syntax check"
info "[3/6] Selecting a zone"
ZONES=()
if [[ -n "${ZONE:-}" ]]; then
  ZONES+=("$ZONE")
else
  DEFAULT_ZONE="$(gcloud config get-value compute/zone 2>/dev/null || true)"
  [[ -n "$DEFAULT_ZONE" && "$DEFAULT_ZONE" != "(unset)" ]] && ZONES+=("$DEFAULT_ZONE")
  while IFS= read -r z; do [[ -n "$z" ]] && ZONES+=("$z"); done < <(
    gcloud compute instances list --project="$PROJECT_ID" --format='value(zone)' 2>/dev/null || true
  )
  ZONES+=(us-central1-a us-east1-b us-west1-b us-central1-b europe-west1-b asia-east1-b asia-southeast1-b)
fi
declare -A SEEN=()
SELECTED=""
EXISTING="$(gcloud compute instances list --project="$PROJECT_ID" --filter="name=$VM_NAME" --format='value(zone)' 2>/dev/null || true)"
if [[ -n "$EXISTING" ]]; then
  SELECTED="$(head -n 1 <<<"$EXISTING")"
  warn "VM already exists in $SELECTED; will not overwrite or recreate it."
else
  info "[4/6] Creating VM; only location-policy failures allow another zone"
  for z in "${ZONES[@]}"; do
    [[ -n "$z" && -z "${SEEN[$z]+x}" ]] || continue
    SEEN[$z]=1
    info "Trying zone: $z"
    if gcloud compute instances create "$VM_NAME" --project="$PROJECT_ID" --zone="$z" \
      --machine-type="$MACHINE_TYPE" \
      --image-project=ubuntu-os-cloud --image-family=ubuntu-2404-lts-amd64 \
      --boot-disk-size=30GB --boot-disk-type=pd-standard \
      --network="$NETWORK" --tags="$TAG" \
      --no-service-account --no-scopes \
      --metadata-from-file="startup-script=$STARTUP" \
      --labels=app=ghost-terminal-ai --quiet >"$LOG" 2>&1; then
      SELECTED="$z"
      break
    fi
    if grep -Eq 'constraints/gcp.resourceLocations|resourceLocations.*violat|Location .*violates constraint' "$LOG"; then
      warn "$z blocked by location policy. Trying another zone."
      continue
    fi
    cat "$LOG" >&2
    die "VM creation blocked for another reason (permission, quota, machine or network)."
  done
  [[ -n "$SELECTED" ]] || die "No candidate zone was permitted. Try ZONE=your-allowed-zone."
fi
info "[5/6] Allowing public ports 80 and 443 for tagged VM only"
if ! gcloud compute firewall-rules describe "$FIREWALL_RULE" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud compute firewall-rules create "$FIREWALL_RULE" \
    --project="$PROJECT_ID" --network="$NETWORK" --direction=INGRESS \
    --allow=tcp:80,tcp:443 --source-ranges=0.0.0.0/0 \
    --target-tags="$TAG" --quiet || warn "Firewall creation failed; public site may be unreachable."
else
  warn "Existing firewall rule preserved: $FIREWALL_RULE"
fi
info "[6/6] Getting public URL and recovery commands"
IP="$(gcloud compute instances describe "$VM_NAME" --project="$PROJECT_ID" --zone="$SELECTED" \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null || true)"
[[ -n "$IP" ]] || die "VM exists, but external IP is missing."
printf '\n%s\n' '==================== VM CREATED ===================='
printf 'Project: %s\nVM: %s\nZone: %s\nIP: %s\n' "$PROJECT_ID" "$VM_NAME" "$SELECTED" "$IP"
printf 'Candidate HTTPS URL: https://%s.sslip.io\n' "$IP"
printf '%s\n' 'Setup continues ON THE VM independently of Cloud Shell.'
printf '%s\n' 'The URL works only after app setup and HTTPS certificate issuance.'
printf '\nCheck setup logs:\n'
printf 'gcloud compute ssh %s --project=%s --zone=%s --command="sudo tail -n 100 /var/log/ghost-terminal-bootstrap.log"\n' "$VM_NAME" "$PROJECT_ID" "$SELECTED"
printf '\nCheck application services:\n'
printf 'gcloud compute ssh %s --project=%s --zone=%s --command="sudo systemctl --no-pager status ghost-terminal ollama caddy"\n' "$VM_NAME" "$PROJECT_ID" "$SELECTED"
printf '\nStop billing after demo:\n'
printf 'gcloud compute instances stop %s --project=%s --zone=%s\n' "$VM_NAME" "$PROJECT_ID" "$SELECTED"
