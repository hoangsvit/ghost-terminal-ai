#!/usr/bin/env bash
# ePlus.DEV - Ghost Terminal AI: provision once, or update an existing GCE VM.
# This script does NOT delete resources or overwrite an existing application checkout.
set -Eeuo pipefail
C_RESET=$'\033[0m'; C_GREEN=$'\033[0;32m'; C_BLUE=$'\033[0;34m'; C_YELLOW=$'\033[0;33m'
info(){ printf '%s%s%s\n' "$C_BLUE" "$*" "$C_RESET"; }
warn(){ printf '%s%s%s\n' "$C_YELLOW" "$*" "$C_RESET" >&2; }
die(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage(){ cat <<'HELP'
ePlus.DEV - Ghost Terminal AI | Provision or update a Compute Engine VM

  bash vm/deploy.sh --ref main
  bash vm/deploy.sh --project PROJECT_ID --ref main
  bash vm/deploy.sh --zone us-east1-d --ref feature/my-branch

Arguments: --project ID, --zone ZONE, --vm NAME, --ref BRANCH,
           --no-wait (return after creating the VM, startup continues there), --help.
Environment: PROJECT_ID, ZONE, VM_NAME, REF, MACHINE_TYPE, NETWORK, FIREWALL_RULE.
Warning: creating a VM, persistent disk and public IPv4 can incur cloud charges.
HELP
}
PROJECT_ID="${PROJECT_ID:-}"
ZONE="${ZONE:-}"
VM_NAME="${VM_NAME:-ghost-terminal-ai-vm}"
REF="${REF:-main}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-standard-2}"
NETWORK="${NETWORK:-default}"
FIREWALL_RULE="${FIREWALL_RULE:-ghost-terminal-ai-web}"
TAG=ghost-terminal-ai-web
WAIT=1
while (( $# )); do
  case "$1" in
    --project|--zone|--vm|--ref)
      [[ $# -ge 2 && -n "$2" ]] || die "Missing value for $1"
      case "$1" in
        --project) PROJECT_ID="$2";;
        --zone) ZONE="$2";;
        --vm) VM_NAME="$2";;
        --ref) REF="$2";;
      esac
      shift 2;;
    --no-wait) WAIT=0; shift;;
    -h|--help) usage; exit 0;;
    *) die "Unknown argument: $1";;
  esac
done
[[ "$REF" =~ ^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,127}$ &&
    "$REF" != *..* && "$REF" != */ && "$REF" != *.lock ]] || die "Invalid Git branch: $REF"
[[ "$VM_NAME" =~ ^[a-z][a-z0-9-]{0,62}$ ]] || die "Invalid VM name"
[[ -z "$ZONE" || "$ZONE" =~ ^[a-z][a-z0-9-]+$ ]] || die "Invalid zone"
[[ -z "$PROJECT_ID" || "$PROJECT_ID" =~ ^[a-z][a-z0-9-]+$ ]] || die "Invalid project ID"
for executable in gcloud curl python3 bash; do
  command -v "$executable" >/dev/null || die "Missing command: $executable"
done
printf '%s\n' "${C_GREEN}ePlus.DEV - Starting Execution${C_RESET}"
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
[[ -n "$PROJECT_ID" && "$PROJECT_ID" != "(unset)" ]] || die "No Google Cloud project selected; pass --project ID."
info "Ghost Terminal AI | Project=$PROJECT_ID | Ref=$REF | VM=$VM_NAME"
[[ "$PROJECT_ID" == qwiklabs-* ]] && warn "Qwiklabs project is temporary and can restrict permissions/regions."
warn "Creating a VM, persistent disk and public IP can incur charges. Only proceed in the intended project."
info "[1/6] Confirm Compute Engine API"
gcloud services enable compute.googleapis.com --project="$PROJECT_ID" --quiet ||
  die "Cannot enable Compute Engine API. Verify permissions and lab restrictions."

info "[2/6] Locate existing VM (do not assume absence when listing fails)"
if ! INSTANCES="$(gcloud compute instances list --project="$PROJECT_ID" \
  --format='csv[no-heading](name,zone,status)')"; then
  die "Could not list VMs in $PROJECT_ID. Check IAM/API access; NOT treating this as an empty project."
fi
EXISTING_ZONE=""
EXISTING_STATUS=""
FOUND=0
while IFS=',' read -r found_name found_zone found_status; do
  [[ "$found_name" == "$VM_NAME" ]] || continue
  FOUND=$((FOUND+1))
  EXISTING_ZONE="${found_zone##*/}"
  EXISTING_STATUS="$found_status"
done <<< "$INSTANCES"
(( FOUND <= 1 )) || die "Multiple VMs share name $VM_NAME. Select a zone explicitly."
if (( FOUND == 1 )); then
  if [[ -n "$ZONE" && "$ZONE" != "$EXISTING_ZONE" ]]; then
    die "VM exists in $EXISTING_ZONE, not requested $ZONE; refusing to create a duplicate."
  fi
  info "Existing VM found in $EXISTING_ZONE ($EXISTING_STATUS). Updating without recreation."
  UPDATER="$(mktemp)"
  trap 'rm -f "$UPDATER"' EXIT
  curl -fsSL --retry 3 \
    "https://raw.githubusercontent.com/hoangsvit/ghost-terminal-ai/$REF/vm/update.sh" \
    -o "$UPDATER" || die "Cannot fetch vm/update.sh from branch $REF."
  bash -n "$UPDATER" || die "Downloaded updater is invalid."
  bash "$UPDATER" --project "$PROJECT_ID" --zone "$EXISTING_ZONE" \
    --vm "$VM_NAME" --ref "$REF"
  exit $?
fi

info "[3/6] Download and validate versioned startup script"
STARTUP="$(mktemp)"
LOG="$(mktemp)"
trap 'rm -f "$STARTUP" "$LOG"' EXIT
curl -fsSL --retry 3 \
  "https://raw.githubusercontent.com/hoangsvit/ghost-terminal-ai/$REF/vm/startup.sh" \
  -o "$STARTUP" || die "Cannot fetch vm/startup.sh from branch $REF."
bash -n "$STARTUP" || die "Downloaded startup script has invalid shell syntax."
ZONES=()
if [[ -n "$ZONE" ]]; then
  ZONES+=("$ZONE")
else
  DEFAULT_ZONE="$(gcloud config get-value compute/zone 2>/dev/null || true)"
  [[ -n "$DEFAULT_ZONE" && "$DEFAULT_ZONE" != "(unset)" ]] && ZONES+=("$DEFAULT_ZONE")
  ZONES+=(us-east1-d us-east1-b us-central1-a us-central1-b us-west1-b asia-east1-b asia-southeast1-b europe-west1-b)
fi
info "[4/6] Create new VM (try alternative zones only for location-policy violations)"
SELECTED=""
declare -A TRIED=()
for z in "${ZONES[@]}"; do
  [[ -n "$z" && -z "${TRIED[$z]+x}" ]] || continue
  TRIED[$z]=1
  info "Trying zone: $z"
  if gcloud compute instances create "$VM_NAME" \
    --project="$PROJECT_ID" --zone="$z" \
    --machine-type="$MACHINE_TYPE" --image-project=ubuntu-os-cloud \
    --image-family=ubuntu-2404-lts-amd64 \
    --boot-disk-size=30GB --boot-disk-type=pd-standard \
    --network="$NETWORK" --tags="$TAG" \
    --no-service-account --no-scopes \
    --metadata="ghost-repo-ref=$REF" \
    --metadata-from-file="startup-script=$STARTUP" \
    --labels=app=ghost-terminal-ai --quiet >"$LOG" 2>&1; then
    SELECTED="$z"
    break
  fi
  if grep -Eqi 'constraints/gcp.resourceLocations|location .*violat.*constraint|resourceLocations.*violat' "$LOG"; then
    warn "Zone $z restricted by organization policy; trying next zone."
    continue
  fi
  cat "$LOG" >&2
  die "VM creation failed due to IAM, quota, API, networking, zone availability or another error. Existing resources were not deleted."
done
[[ -n "$SELECTED" ]] || die "All candidate zones were disallowed. Set --zone to a permitted zone."
info "Created VM $VM_NAME in $SELECTED. Startup runs independently on the VM."

info "[5/6] Configure required network access (80/443, tagged VM only)"
if gcloud compute firewall-rules describe "$FIREWALL_RULE" \
  --project="$PROJECT_ID" --format=json >"$LOG" 2>/dev/null; then
  # Verify that an existing rule is truly adequate; do not silently accept a wrong rule.
  python3 - "$LOG" "$NETWORK" "$TAG" <<'PY' ||
    die "Firewall rule $FIREWALL_RULE already exists but is not adequate. Review it manually (no automatic overwrite)."
import json, sys
rule = json.load(open(sys.argv[1], encoding="utf-8"))
network, tag = sys.argv[2:]
if rule.get("direction") != "INGRESS" or rule.get("disabled", False):
    sys.exit(1)
if rule.get("network", "").split("/")[-1] != network:
    sys.exit(1)
if tag not in rule.get("targetTags", []):
    sys.exit(1)
ranges = rule.get("sourceRanges", [])
if "0.0.0.0/0" not in ranges:
    sys.exit(1)
ports = set()
for item in rule.get("allowed", []):
    if item.get("IPProtocol") == "tcp":
        ports.update(item.get("ports", []) or [])
if not {"80", "443"}.issubset(ports):
    sys.exit(1)
PY
else
  gcloud compute firewall-rules create "$FIREWALL_RULE" \
    --project="$PROJECT_ID" --network="$NETWORK" --direction=INGRESS \
    --allow=tcp:80,tcp:443 --source-ranges=0.0.0.0/0 \
    --target-tags="$TAG" --quiet ||
    die "VM created but firewall creation failed. Check Compute Engine firewall permissions."
fi
IP="$(gcloud compute instances describe "$VM_NAME" --project="$PROJECT_ID" --zone="$SELECTED" \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)')"
[[ -n "$IP" ]] || die "VM created without public IPv4. Inspect network/address configuration."
URL="https://$IP.sslip.io"
printf 'VM: %s | Project: %s | Zone: %s | Public URL: %s\n' "$VM_NAME" "$PROJECT_ID" "$SELECTED" "$URL"
if (( ! WAIT )); then
  warn "Startup continues on VM. HTTPS and model readiness NOT confirmed (--no-wait)."
  exit 0
fi
info "[6/6] Verify external HTTPS and Gemma readiness (initial model pull can be slow)"
READY=0
for i in {1..90}; do
  # Do not bypass TLS verification or claim success based on an HTTP 200 from the wrong app.
  if BODY="$(curl -fsS --connect-timeout 4 --max-time 8 "$URL/api/health" 2>/dev/null)" &&
     python3 -c 'import sys,json; d=json.load(sys.stdin); assert d.get("ready") is True and d.get("deployment")=="vm"' <<<"$BODY"; then
    READY=1
    break
  fi
  if (( i % 6 == 1 )); then info "Waiting for VM bootstrap/HTTPS/Gemma ($i/90) ..."; fi
  sleep 10
done
if (( ! READY )); then
  warn "VM was created, but external HTTPS/model readiness was NOT verified."
  warn "Review startup logs with:"
  warn "gcloud compute ssh $VM_NAME --project=$PROJECT_ID --zone=$SELECTED --command='sudo tail -n 120 /var/log/ghost-terminal-bootstrap.log'"
  warn "Also check: gcloud compute ssh $VM_NAME --project=$PROJECT_ID --zone=$SELECTED --command='sudo systemctl status ghost-terminal ollama caddy --no-pager'"
  die "Deployment incomplete (VM preserved for repair; no destructive rollback)."
fi
printf '%s\n' "${C_GREEN}DEPLOYMENT VERIFIED: $URL${C_RESET}"
printf 'Model health: %s\n' "$BODY"
