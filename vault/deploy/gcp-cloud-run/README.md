[🏠 Deploy Hub](../../00-START-HERE.md) › **GCP Cloud Run**

# Deploy on GCP Cloud Run

**Status: 🚧 planned (Phase D1)** — the image is already Cloud Run-ready (it honours the
injected `$PORT`; verified). What works today, manually:

```bash
gcloud run deploy sg-send-vault \
  --image docker.io/diniscruz/sg-send-vault:latest \
  --region europe-west2 --allow-unauthenticated --memory 1Gi \
  --set-env-vars SEND__STORAGE_MODE=memory,SGRAPH_SEND__ACCESS_TOKEN=<your-key>
```

Storage: `memory` for ephemeral use today; durable S3 (cross-cloud creds) and a native GCS
backend are on the roadmap. Terraform module + CI deploy land with Phase D1.
