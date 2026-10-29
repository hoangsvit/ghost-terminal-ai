#!/usr/bin/env bash
# One command: update an existing VM, or safely provision a new VM in the selected GCP project.
set -Eeuo pipefail
RESET=$'\033[0m'; GREEN=$'\033[0;32m'; BLUE=$'\033[0;34m'; YELLOW=$'\033[0;33m'
info(){ printf '%s%s%s\n' "$BLUE" "$*" "$RESET"; }
warn(){ printf '%s%s%s\n' "$YELLOW" "$*" "$RESET" >&2; }
die(){ echo "ERROR: $*" >&2; exit 1; }

MODE=deploy
AUTO_CREATE=1
REF="${REF:-main}"
PROJECT_ID="${PROJECT_ID:-}"
ZONE="${ZONE:-}"
VM_NAME="${VM_NAME:-ghost-terminal-ai-vm}"

usage(){
  cat <<'HELP'
ePlus.DEV | Ghost Terminal AI — Deploy or update an existing Compute Engine VM

  bash vm/update.sh --ref main
  bash vm/update.sh --ref feature/my-reviewed-branch
  bash vm/update.sh --status
  bash vm/update.sh --rollback
  bash vm/update.sh --no-create --ref main

Options:
  --ref BRANCH    Git branch to deploy (default: main)
  --project ID    Google Cloud project (default: current gcloud project)
  --zone ZONE     VM zone (default: auto-detect)
  --vm NAME       VM name (default: ghost-terminal-ai-vm)
  --status        Inspect running version and service without modifying VM
  --rollback      Restore previous deployed commit
  --no-create     Fail if VM is missing instead of provisioning one
  --help          Show this help

Deploy mode provisions a new VM when none exists in the selected project.
New VM, disk and public IP may incur charges. Existing VM keeps Ollama/model weights.
HELP
}
while (( $# )); do
  case "$1" in
    --ref|--project|--zone|--vm)
      [[ $# -ge 2 && -n "$2" ]] || die "Missing value for $1"
      case "$1" in
        --ref) REF="$2" ;; --project) PROJECT_ID="$2" ;;
        --zone) ZONE="$2" ;; --vm) VM_NAME="$2" ;;
      esac
      shift 2 ;;
    --ref=*) REF="${1#*=}"; shift ;;
    --project=*) PROJECT_ID="${1#*=}"; shift ;;
    --zone=*) ZONE="${1#*=}"; shift ;;
    --vm=*) VM_NAME="${1#*=}"; shift ;;
    --no-create) AUTO_CREATE=0; shift ;;
    --status) [[ "$MODE" == deploy ]] || die "Choose one mode"; MODE=status; shift ;;
    --rollback) [[ "$MODE" == deploy ]] || die "Choose one mode"; MODE=rollback; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done
[[ "$REF" =~ ^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,127}$ &&
   "$REF" != *..* && "$REF" != */ && "$REF" != *.lock ]] || die "Invalid Git branch"
[[ "$VM_NAME" =~ ^[a-z][a-z0-9-]{0,62}$ ]] || die "Invalid VM name"
[[ -z "$ZONE" || "$ZONE" =~ ^[a-z][a-z0-9-]+$ ]] || die "Invalid zone"
[[ -z "$PROJECT_ID" || "$PROJECT_ID" =~ ^[a-z][a-z0-9-]+$ ]] || die "Invalid project ID"

command -v gcloud >/dev/null || die "Run this script in Google Cloud Shell"
printf '%s\n' "${GREEN}ePlus.DEV - Starting Execution${RESET}"
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
[[ -n "$PROJECT_ID" && "$PROJECT_ID" != "(unset)" ]] || die "Select project or use --project."
info "[1/3] Locate VM in explicitly selected project: $PROJECT_ID"
# A permissions/API error must not be interpreted as "VM does not exist".
if ! FOUND_VMS="$(gcloud compute instances list --project="$PROJECT_ID" \
  --format='csv[no-heading](name,zone,status)')"; then
  die "Unable to list instances in $PROJECT_ID. Check Cloud IAM/API permissions."
fi
FOUND=0
DETECTED_ZONE=""
STATUS=""
while IFS=',' read -r name vm_zone vm_status; do
  [[ "$name" == "$VM_NAME" ]] || continue
  FOUND=$((FOUND+1))
  DETECTED_ZONE="${vm_zone##*/}"
  STATUS="$vm_status"
done <<< "$FOUND_VMS"
(( FOUND <= 1 )) || die "Multiple instances named $VM_NAME found; specify --zone."
if (( FOUND == 0 )); then
  [[ "$MODE" == deploy ]] || die "VM $VM_NAME does not exist in $PROJECT_ID; cannot $MODE."
  (( AUTO_CREATE )) || die "VM missing in $PROJECT_ID and --no-create was specified."
  warn "No $VM_NAME VM in project $PROJECT_ID. Provisioning a NEW VM in this project (may incur charges)."
  # Fetch matching deploy script from the SAME selected branch; safe even with no local clone.
  command -v curl >/dev/null || die "curl required to download the provisioning script"
  DEPLOY_SCRIPT="$(mktemp)"
  trap 'rm -f "$DEPLOY_SCRIPT"' EXIT
  curl -fsSL --retry 3 \
    "https://raw.githubusercontent.com/hoangsvit/ghost-terminal-ai/$REF/vm/deploy.sh" \
    -o "$DEPLOY_SCRIPT" || die "Could not download vm/deploy.sh for $REF."
  bash -n "$DEPLOY_SCRIPT" || die "Downloaded provisioning script has invalid syntax."
  COMMAND=(bash "$DEPLOY_SCRIPT" --ref "$REF" --project "$PROJECT_ID" --vm "$VM_NAME")
  [[ -z "$ZONE" ]] || COMMAND+=(--zone "$ZONE")
  "${COMMAND[@]}"
  exit $?
fi
if [[ -n "$ZONE" && "$ZONE" != "$DETECTED_ZONE" ]]; then
  die "Found $VM_NAME in $DETECTED_ZONE, not $ZONE; refusing to modify a different VM."
fi
ZONE="$DETECTED_ZONE"
if [[ "$STATUS" != RUNNING ]]; then
  if [[ "$STATUS" == TERMINATED && "$MODE" == deploy ]]; then
    warn "Existing VM is stopped. Starting it (billing may resume)."
    gcloud compute instances start "$VM_NAME" --project="$PROJECT_ID" --zone="$ZONE" --quiet ||
      die "Failed to start existing VM."
  else
    die "VM is $STATUS; cannot run mode $MODE. Start the VM explicitly first."
  fi
fi
info "[2/3] VM=$VM_NAME | Zone=$ZONE | Mode=$MODE | Ref=$REF"
[[ "$PROJECT_ID" == qwiklabs-* ]] && warn "Qwiklabs VM may expire at lab end."
IP="$(gcloud compute instances describe "$VM_NAME" --project="$PROJECT_ID" --zone="$ZONE" \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null || true)"

info "[3/3] Connect over SSH and update app only"
gcloud compute ssh "$VM_NAME" --project="$PROJECT_ID" --zone="$ZONE" \
  --command="sudo bash -s -- '$MODE' '$REF'" <<'REMOTE'
set -Eeuo pipefail
MODE="$1"; REF="$2"
APP=/opt/ghost-terminal-ai
STATE=/var/lib/ghost-terminal-ai
HISTORY="$STATE/previous-deployed-sha"
echo "===== ePlus.DEV | Ghost Terminal VM updater ====="
[[ -d "$APP/.git" ]] || { echo "ERROR: Missing repository in $APP"; exit 1; }
id ghostapp >/dev/null || exit 1
mkdir -p "$STATE"
exec 9>"$STATE/update.lock"
flock -n 9 || { echo "ERROR: Another deploy is running"; exit 1; }
gitapp(){ sudo -u ghostapp -H git -C "$APP" "$@"; }
health(){
  local count path
  path="$(mktemp)"
  for count in {1..15}; do
    if systemctl is-active --quiet ghost-terminal &&
       curl -fsS --max-time 5 http://127.0.0.1:8765/api/health -o "$path" 2>/dev/null &&
       python3 -c 'import json,sys; assert json.load(open(sys.argv[1])).get("ready") is True' "$path"; then
      cat "$path"; printf '\n'
      rm -f "$path"
      return 0
    fi
    echo "Health retry $count/15"; sleep 2
  done
  rm -f "$path"
  return 1
}
current="$(gitapp rev-parse HEAD)"
if [[ "$MODE" == status ]]; then
  echo "Current commit: $current"
  systemctl --no-pager is-active ghost-terminal ollama caddy || true
  health
  exit $?
fi
if [[ -n "$(gitapp status --porcelain)" ]]; then
  echo "ERROR: Uncommitted changes found; refusing to overwrite:"
  gitapp status --short
  exit 1
fi
if [[ "$MODE" == rollback ]]; then
  [[ -f "$HISTORY" ]] || { echo "ERROR: No previous commit recorded"; exit 1; }
  target="$(cat "$HISTORY")"
  [[ "$target" =~ ^[a-f0-9]{40}$ ]] || { echo "ERROR: Invalid backup SHA"; exit 1; }
  gitapp cat-file -e "$target^{commit}"
else
  echo "Fetching origin branch $REF"
  gitapp fetch --no-tags origin "refs/heads/$REF"
  target="$(gitapp rev-parse 'FETCH_HEAD^{commit}')"
fi
echo "Current: $current"
echo "Target:  $target"
if [[ "$current" == "$target" ]]; then
  echo "Already up-to-date; checking health."
  if ! health; then
    systemctl restart ghost-terminal
    health || { journalctl -u ghost-terminal -n 60 --no-pager; exit 1; }
  fi
  exit 0
fi
recover(){
  local result="$?"
  trap - ERR
  echo "ERROR: Update failed. Restoring commit $current" >&2
  if gitapp switch --detach "$current" && systemctl restart ghost-terminal; then
    health || echo "WARNING: Previous version is not healthy" >&2
  else
    echo "CRITICAL: Auto-rollback failed; inspect VM manually" >&2
  fi
  exit "$result"
}
trap recover ERR
# Preserve the prior commit as an explicit local ref so shallow-clone GC cannot lose it.
gitapp update-ref refs/ghost-terminal/previous "$current"
echo "$current" > "$HISTORY"
gitapp switch --detach "$target"
systemctl restart ghost-terminal
health || { journalctl -u ghost-terminal -n 60 --no-pager; false; }
trap - ERR
echo "SUCCESS: Deployed $target"
REMOTE
[[ -n "$IP" ]] || die "App updated but VM has no public IPv4 address. Cannot verify HTTPS."
URL="https://$IP.sslip.io"
info "Verifying public HTTPS at $URL/api/health ..."
PUBLIC_READY=0
for check in {1..12}; do
  if RESPONSE="$(curl -fsS --connect-timeout 5 --max-time 10 "$URL/api/health" 2>/dev/null)" &&
    python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("ready") is True and d.get("deployment")=="vm"' <<< "$RESPONSE"; then
    PUBLIC_READY=1
    break
  fi
  info "Public HTTPS pending ($check/12)"
  sleep 5
done
(( PUBLIC_READY )) || die "Application updated, but public HTTPS was not verified. Check Caddy, DNS/certificate and ingress 80/443."
printf '%sWebsite verified: %s%s\n' "$GREEN" "$URL" "$RESET"
printf '%s\n' "${GREEN}SUCCESS. Existing VM updated; Ollama, model and disk preserved.${RESET}"
