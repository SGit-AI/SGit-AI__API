[🏠 Deploy Hub](../../00-START-HERE.md) › **Docker**

# Deploy with Docker — works today

A single self-contained image: the SG/Send API plus the vault web UI on one port. No external dependencies, no runtime downloads — it works air-gapped.

## 60-second start (ephemeral)

```bash
docker run --rm -p 8080:8080 diniscruz/sg-send-vault:latest
```

Open <http://localhost:8080/> → create or open a vault. Data lives in the container's writable layer and is discarded on exit.

## Persistent

```bash
docker run -d --restart=unless-stopped \
  -p 8080:8080 \
  -v "$(pwd)/_sg-send_data:/data" \
  --name sg-send \
  diniscruz/sg-send-vault:latest
```

## Protected (recommended for anything reachable from outside your machine)

```bash
docker run -d --restart=unless-stopped \
  -p 8080:8080 \
  -v /var/lib/sg-send:/data \
  -e SGRAPH_SEND__ACCESS_TOKEN=$(openssl rand -hex 32) \
  --name sg-send \
  diniscruz/sg-send-vault:latest
```

Every request then needs the header `x-sgraph-access-token: <token>` — or set it once as a browser cookie at `http://localhost:8080/auth/set-cookie-form`.

## Point sgit at it

```bash
sgit clone <vault-key> --endpoint http://localhost:8080 --token <access-token>
```

## Memory-only mode (ephemeral / agentic)

```bash
docker run --rm -p 8080:8080 -e SEND__STORAGE_MODE=memory diniscruz/sg-send-vault:latest
```

Nothing touches disk; when the container stops, everything is gone. By design. This mode makes **zero external calls** — usable fully offline.

## HTTPS

The vault UI needs a **secure context** (Web Crypto): `http://localhost` works; any other plain-HTTP host does not. Options:

1. Reverse proxy with auto-TLS (simplest — Caddy): `send.example.com { reverse_proxy localhost:8080 }`
2. Native TLS in the container: `-e FAST_API__TLS__ENABLED=true -v $(pwd)/certs:/certs:ro -p 443:443` (expects `/certs/cert.pem` + `/certs/key.pem`; fails loud if missing — never a silent HTTP fallback)

## S3-backed

```bash
docker run -d -p 8080:8080 \
  -e SEND__STORAGE_MODE=s3 -e SEND__S3_BUCKET=my-sg-send-bucket \
  -e AWS_ACCESS_KEY_ID=… -e AWS_SECRET_ACCESS_KEY=… -e AWS_DEFAULT_REGION=… \
  diniscruz/sg-send-vault:latest
```

## Air-gapped

```bash
docker save diniscruz/sg-send-vault:latest | gzip > sg-send-vault.tar.gz
# transfer, then:
gunzip -c sg-send-vault.tar.gz | docker load
```

The image has no runtime external dependencies — the vault UI never calls out.

## Facts

| | |
|---|---|
| Image | `diniscruz/sg-send-vault` (Docker Hub) |
| Tags | `:latest` and immutable `:vX.Y.Z` |
| Architectures | linux/amd64 + linux/arm64 (Apple Silicon, Graviton, RPi 4+) |
| Size | ~250 MB |
| Port | 8080 (HTTP) / 443 (native TLS mode) |
| Health | `GET /api/info/health` → `{"status":"ok"}` |
| Config | [full environment-variable reference](../../reference/configuration.md) |

Next: [EC2 with your own domain](../aws-ec2/README.md) · [Configuration reference](../../reference/configuration.md)
