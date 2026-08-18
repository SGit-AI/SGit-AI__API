[🏠 Deploy Hub](../00-START-HERE.md) › **Configuration**

# Configuration Reference

All configuration is environment variables — identical across Docker, Lambda, EC2, Fargate,
Cloud Run, and Heroku.

| Variable | Default | Purpose |
|---|---|---|
| `SEND__STORAGE_MODE` | `disk` (container) | `memory` \| `disk` \| `s3` |
| `SEND__DISK_PATH` | `/data` | filesystem path in disk mode |
| `SEND__S3_BUCKET` | auto (`{account}--sgraph-send-transfers--{region}`) | explicit bucket in s3 mode |
| `SGRAPH_SEND__ACCESS_TOKEN` | unset (open) | the access key — when set, gates every route incl. reads |
| `PORT` | `8080` | HTTP port (Cloud Run/Heroku inject it) |
| `FAST_API__TLS__ENABLED` | `false` | native TLS switch |
| `FAST_API__TLS__CERT_FILE` / `KEY_FILE` | `/certs/cert.pem` / `key.pem` | mounted cert pair |
| `FAST_API__TLS__PORT` | `8443` | TLS bind port (non-root container; host-map `-p 443:8443`) |
| `SEND__STORAGE_BASE` / `SEND__STORAGE_VERSION` / `SEND__DEPLOYMENT_ID` | empty | multi-tenant path prefix pieces (deploy-time only — changing them orphans existing data) |
