# Deploy Ghost Terminal AI to Google Compute Engine VM

This deployment is for a **public demonstration**, running **Gemma 3 1B through Ollama**. It uses Ubuntu 24.04, the repository's Python server, systemd and Caddy (HTTPS reverse proxy). **No Cloud Run, Cloud Build, Firebase, Vertex AI, or GitHub-to-GCP integration** is needed.

> Hosted mode is **not local to the visitor's device**. Input travels to the Compute Engine VM for inference. Never paste credentials or private logs. Input redaction is best effort. Caddy uses an external `sslip.io` DNS name; this is a third-party domain service, not an official Google Cloud domain.

## Quick start: one command for any GCP project

In Google Cloud Shell, select the *intended project*. You can explicitly supply its ID to avoid confusing temporary Qwiklabs projects:

```bash
curl -fsSL https://raw.githubusercontent.com/hoangsvit/ghost-terminal-ai/main/vm/update.sh -o /tmp/ghost-update.sh
bash /tmp/ghost-update.sh --project YOUR_PROJECT_ID --ref main
```

**If the project contains no `ghost-terminal-ai-vm`, the script now creates it automatically.** A new deployment installs Ollama + Gemma 3 1B, configures a tagged firewall rule for ports 80/443, starts Caddy, and checks the public HTTPS health endpoint until `ready: true` and `deployment: vm`. If a VM is already running, it updates application code and verifies local + public health. A stopped VM is started in deploy mode. It will **not** silently claim success when it lacks required IAM permissions, region quota, HTTPS or model availability.

You can specify `--zone us-east1-d` if your lab has an allowed zone. A new VM incurs Compute Engine/disk/public IP charges. When the default region is restricted by organization policy, the provisioner attempts a small list of candidate regions; other errors terminate immediately. No automatic resource deletion occurs on failure.

To check an existing VM without mutation: `bash /tmp/ghost-update.sh --project YOUR_PROJECT_ID --status`. To disallow provisioning: `--no-create`. To revert the last code update: `--rollback`.

The first bootstrap downloads the model (possibly several minutes). If Cloud Shell disconnects, the VM's GCE startup script continues; rerun the deploy command to inspect/update the existing resource rather than creating another VM. If bootstrap does not finish, inspect `/var/log/ghost-terminal-bootstrap.log` on that VM. The script reports a nonzero exit instead of inventing a working URL.

## Architecture

```text
Browser -> HTTPS:443 -> Caddy -> 127.0.0.1:8765 Python
                                     -> 127.0.0.1:11434 Ollama
                                         -> gemma3:1b (persisted on VM disk)
```

Only **ports 80 and 443** are opened through a firewall rule restricted by VM network tag. Port 8765 (web app) and 11434 (Ollama) stay loopback-only. A small in-memory rate limit protects a small public demo (3 AI requests per minute per VM, not per visitor).

## Option A: one-script deploy via Cloud Shell

Select the intended GCP project first. Check billing; Compute Engine, its disk and public IPv4 address **can incur charges even when the demo is idle**. Qwiklabs projects are temporary and resource creation can be prohibited by Organization Policy.

```bash
curl -fsSL https://raw.githubusercontent.com/hoangsvit/ghost-terminal-ai/main/vm/deploy.sh -o /tmp/ghost-deploy.sh
bash /tmp/ghost-deploy.sh --project YOUR_PROJECT_ID --ref main
```

This alternate direct provisioner also detects existing VMs and delegates to the updater. The recommended single entrypoint is `vm/update.sh` above.

The wrapper enables the Compute Engine API, chooses an existing/default zone first, and tries alternative zones **only for resource-location-policy errors**. It creates an Ubuntu VM `ghost-terminal-ai-vm`, default `e2-standard-2` (2 vCPU / 8 GB RAM), with a 30 GB persistent disk. The startup script runs **on the VM**: cloud terminal disconnects will not kill installation. It downloads Ollama and Gemma exactly once into persistent storage and registers systemd services.

When the VM already exists, the wrapper **does not overwrite its data or reinitialize it**; it calls the updater and validates the deployed code. New VMs carry the requested Git ref in instance metadata so startup installs that exact branch.

Choose a zone explicitly if the lab restricts locations:

```bash
bash /tmp/ghost-update.sh --project YOUR_PROJECT_ID --zone us-central1-a --ref main
```

For the direct provisioner, you may also set `VM_NAME`, `PROJECT_ID`, `REF`, `MACHINE_TYPE`, `NETWORK` and `FIREWALL_RULE` as environment variables before running. No `gcloud auth login` is necessary if Cloud Shell is already authenticated.

### Recovery: Ollama error `panic: $HOME is not defined`

Early VM deployments could install Ollama and then stop before downloading the model because Compute Engine startup metadata does not always provide a `HOME` environment variable.

**No VM deletion or redeployment is required.** Run this command from Cloud Shell; it provides `HOME` to the existing startup script and repeats only installation steps, keeping the existing VM and repository:

```bash
gcloud compute ssh ghost-terminal-ai-vm \
  --project=qwiklabs-gcp-01-dc59a1a9e903 \
  --zone=us-east1-d \
  --command='sudo env HOME=/root bash /opt/ghost-terminal-ai/vm/startup.sh'
```

This VM-specific recovery is for the user's lab project and zone; substitute your own project and zone when needed.

New builds export `HOME=/root` if it is missing. The fix is also covered by CI. On success the startup script creates `ghost-terminal.service`, starts Caddy, and prints the local health check.

### IMPORTANT: first boot finishes separately

When `gcloud compute instances create` succeeds, the script prints a **candidate** URL such as:

```text
https://34-xx-xx-xx.sslip.io
```

Actually, the `sslip.io` hostname uses the IPv4 address **with dots** (for example `https://34.12.34.56.sslip.io`), and Caddy requests a TLS certificate after startup. The default deploy command **waits and verifies HTTPS and model readiness** before announcing a working URL. Use `vm/deploy.sh --no-wait` only when you intentionally want provisioning to continue without that verification.

View setup progress from a fresh Cloud Shell session:

```bash
gcloud compute instances list --filter="name=ghost-terminal-ai-vm"
gcloud compute ssh ghost-terminal-ai-vm --zone=YOUR_ZONE \
  --command="sudo tail -n 100 /var/log/ghost-terminal-bootstrap.log"
gcloud compute ssh ghost-terminal-ai-vm --zone=YOUR_ZONE \
  --command="sudo systemctl --no-pager status ghost-terminal ollama caddy"
```

If SSH is disallowed by Qwiklabs, view the serial console output in Compute Engine, or inspect the VM's startup-script logs.

## Verify the real AI

1. Open the actual VM HTTPS URL and confirm the app loads without a TLS warning.
2. The indicator must show **CLOUD GEMMA 3 READY** (this checks the locally running Ollama model).
3. Under **Story**, choose a synthetic test scenario, click **Load scenario**, then **Awaken the terminal**.
4. Confirm you received a **new generated story**; switch modes and generate again.
5. Record the website and result for the DEV.to challenge.

A GitHub CI pass checks code only and does not mean that Google Cloud deployed correctly.

## Running costs / shutdown

The VM is not a free-tier micro VM. It continues billing while running. After the demo, **stop or delete** it. Stopping a VM stops CPU charges but disks and some IP-related resources may still incur charges; deleting the VM also removes the attached auto-delete boot disk.

```bash
gcloud compute instances stop ghost-terminal-ai-vm --zone=YOUR_ZONE
# Destructive! Only if you no longer need the VM:
gcloud compute instances delete ghost-terminal-ai-vm --zone=YOUR_ZONE
```

Stopping and restarting an instance can change its ephemeral IP, in which case the public `sslip.io` hostname changes. The startup script re-evaluates the external IP on every boot.

### Troubleshooting

- **Location policy:** the project may reject all candidate zones. Don't bypass policy; use an allowed zone/project.
- **No default VPC / firewall permissions:** create a network rule using your own GCP settings, allowing only inbound 80/443 to the VM tag.
- **No HTTPS:** check DNS, firewall ingress on 80/443 and `sudo journalctl -u caddy -n 100 --no-pager`.
- **No AI:** `sudo systemctl status ollama ghost-terminal`, `ollama list`, and `sudo journalctl -u ghost-terminal -n 100`.
- **Cloud Shell disconnect:** do not rerun a new VM creation immediately; check the existing VM via `gcloud compute instances list`.
- **Ollama install fails or quota:** inspect `/var/log/ghost-terminal-bootstrap.log` on the VM.
- **Privacy/security:** use only synthetic sample logs, not private data. Rate limiting is per VM and not a hard cost cap.

References:
- https://docs.cloud.google.com/compute/docs/instances/startup-scripts/linux
- https://docs.cloud.google.com/organization-policy/restrict-locations
- https://packages.ubuntu.com/noble/caddy

## Fast updates for an existing VM

Once the VM exists, **do not rerun the VM creation script to update code**. In Google Cloud Shell:

```bash
bash vm/update.sh --ref main
```

Preview an unmerged PR branch without merging it:

```bash
bash vm/update.sh --ref feature/my-reviewed-change
```

Check service/model health with `bash vm/update.sh --status` and revert to the previous deployed commit with `bash vm/update.sh --rollback`. Project and VM zone are detected automatically. Override with `--project PROJECT_ID --zone ZONE` when necessary.

For Cloud Shell without a repository checkout, download the script from the branch you plan to test, review it, then run it:

```bash
curl -fsSL https://raw.githubusercontent.com/hoangsvit/ghost-terminal-ai/main/vm/update.sh -o /tmp/ghost-update.sh
bash /tmp/ghost-update.sh --ref main
```

**Safety:** In deploy mode, this script **creates a VM when none exists** in the selected project. On an existing VM it does not reinstall Ollama, reload model weights or modify Caddy/firewall rules. Use `--no-create` to forbid provisioning. It refuses to overwrite uncommitted changes and checks `/api/health` after updating. Failed updates trigger an automatic attempt to restore the previous commit. Switching branches on the VM changes the live website; do this only when you intend to preview/deploy. Qwiklabs VMs and sslip.io URLs may expire with the lab.
