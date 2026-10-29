# Deploy Ghost Terminal AI on Google Cloud Run (Gemma 3 + Ollama)

This is an **optional, containerized demo** of the same open-weight Gemma 3 model used by the original local application. No Cloudflare integration, Vertex AI, GPU endpoint, paid API key, or shared inference service is required. Ollama remains on loopback; only the Python website is exposed.

**Cloud hosting is not free by default.** Building and storing an image containing model weights, instance startup, CPU/RAM usage, and traffic may incur costs. The base image uses `ollama/ollama:latest`; pin a tested version or digest for long-lived production deployments.

## Architecture

```text
HTTPS browser -> Cloud Run ingress :$PORT (Python web app)
                                  -> 127.0.0.1:11434 (private Ollama)
                                  -> baked-in gemma3:1b model weights
```

- The model is pulled **when Docker builds the image**, not for every instance start.
- Public requests are handled by the existing Python API.
- The website clearly discloses that log text is sent to a Google Cloud Run instance, not processed locally in the visitor's browser.
- Input uses best-effort secret redaction. Do not paste real credentials or sensitive logs.
- The image accepts only a loopback Ollama endpoint and does not expose its model port publicly.
- An in-memory per-instance budget defaults to 4 AI requests per 60 seconds. Cloud Run max instances 1 helps bound concurrent resource use, but **this is not a global spend cap**.
- The UI waits up to about 270 seconds; the Python Ollama request times out at 240 seconds by default.

## Option A — Use your own Google Cloud deployment method

Build/deploy this repository's `Dockerfile` in any compatible CI/CD workflow and configure the Cloud Run service with:

| Item | Value |
| --- | --- |
| Container entrypoint | `/app/cloudrun/start.sh` (already in image) |
| Ingress port | `8080` (or injected `PORT`) |
| CPU | 2 vCPU to start |
| Memory | 4 GiB to start |
| Concurrency | 1 request per instance |
| Min instances | 0 |
| Max instances | 1 |
| Request timeout | 300 seconds |
| Model | `gemma3:1b` |
| Architecture | Linux amd64 |

No special GCP credentials or API key are needed by this container at runtime.

## Option B — Deploy with Cloud Shell (no local Docker)

Use an existing GCP project with billing enabled:

```bash
gcloud config get-value project
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
git clone --branch feature/google-cloud-run-gemma3 https://github.com/hoangsvit/ghost-terminal-ai.git
cd ghost-terminal-ai

gcloud run deploy ghost-terminal-ai \
  --source . \
  --region asia-southeast1 \
  --execution-environment gen2 \
  --cpu 2 \
  --memory 4Gi \
  --concurrency 1 \
  --min-instances 0 \
  --max-instances 1 \
  --timeout 300 \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars GHOST_INFERENCE_TIMEOUT=240,GHOST_RATE_LIMIT_PER_MINUTE=4
```

Source deployments detect the repo's `Dockerfile`; Cloud Build builds the image and Artifact Registry stores it. The first build downloads the model and may be substantial. Do not claim that the deployment is complete until Cloud Run actually returns its HTTPS service URL.

**For private testing:** omit `--allow-unauthenticated` and access through an authenticated workflow. For a public DEV.to demo, explicitly allow unauthenticated access only after understanding potential resource charges.

## Verify a real AI demo

1. Open the **actual HTTPS URL** returned by Cloud Run (do not guess it).
2. The interface should say **CLOUD GEMMA 3 READY** and explain that log text is processed in Google Cloud.
3. Click **Load sample log**, choose **Haunting**, then **Awaken the terminal**.
4. Confirm an original story is generated (no mock/stub), and switch to Mystery.
5. Check `/api/health` for a ready model and `/api/interpret` for generated text.
6. Record the real demo and attach the URL/video to [DEVTO_SUBMISSION.md](DEVTO_SUBMISSION.md) before publishing.

```bash
gcloud run services describe ghost-terminal-ai --region asia-southeast1 --format 'value(status.url)'
gcloud run services logs read ghost-terminal-ai --region asia-southeast1 --limit 50
```

## Common problems

- **Cloud Run does not become ready:** verify port `PORT`, CPU/RAM and model preload; inspect logs.
- **CLOUD GEMMA 3 OFFLINE / 503:** Ollama startup failed, image omitted the weights, or the CPU model timed out.
- **Very slow inference:** lower `num_predict`, increase CPU, or evaluate a GPU deployment with measured cost.
- **429 public demo busy:** limit of 4 generations/minute per instance has been reached.
- **High costs:** set billing budget alerts, consider Cloud Run min instances 0, max instances 1, disable service when finished. Max instances controls capacity, not a hard billing limit.
- **Build permissions:** verify Cloud Build service account, Artifact Registry write rights and Cloud Run deployer permissions.

## Test code changes

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q app.py ghost_terminal
bash -n cloudrun/start.sh
```

These tests cannot prove a successful model download or real cloud inference without an actual Docker build and deployment.

Docs:
- [Cloud Run source deploy using Dockerfile](https://docs.cloud.google.com/run/docs/deploying-source-code)
- [Container runtime contract](https://docs.cloud.google.com/run/docs/container-contract)
- [Ollama + Gemma on Cloud Run](https://docs.cloud.google.com/run/docs/tutorials/gpu-gemma-with-ollama)
