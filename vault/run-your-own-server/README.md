Every `sgit` user needs a live SG/Send server to push to. You can use the hosted one at `send.sgraph.ai` — or run your own, and this vault shows you how.

**What you get when you run your own:** the full SG/Send API (transfers, vaults, presigned uploads) plus the vault web UI, served from one process. Zero-knowledge by construction — your server only ever stores ciphertext; keys never leave the browser or CLI. Point sgit at it with `sgit clone <vault-key> --endpoint https://your-server`.

**Choose your path:**

| You want | Go to | Status |
|---|---|---|
| A server running in the next 60 seconds | [Docker](../deploy/docker/README.md) | ✅ available today |
| Serverless on AWS, pay-per-request | [AWS Lambda](../deploy/aws-lambda/README.md) | 🚧 templates in progress |
| A dedicated box with your own domain | [AWS EC2](../deploy/aws-ec2/README.md) | 🚧 AMI + template in progress |
| A scaled cluster behind a load balancer | [ECS / Fargate](../deploy/aws-fargate/README.md) | 🚧 template in progress |
| Google Cloud | [Cloud Run](../deploy/gcp-cloud-run/README.md) | 🚧 in progress |
| Heroku | [Heroku](../deploy/heroku/README.md) | 🚧 in progress |
| To publish a vault read-only, no server at all | [Static hosting](../deploy/static-hosting/README.md) | ✅ static mode shipped; exporter in progress |

**Status legend** — ✅ works today, exactly as documented. 🚧 the deployment scripts are being built in the open ([SGraph-AI__App__Send](https://github.com/the-cyber-boardroom/SGraph-AI__App__Send)); each page states precisely what exists now and what is coming, and this vault is updated as each piece ships.

**The three storage modes** (all deployments support them): `memory` — nothing persisted, dies with the process, perfect for ephemeral/agentic work; `disk` — a directory or mounted volume; `s3` — durable object storage for production. Details: [storage modes](../reference/storage-modes.md).

**One key to rule the deployment:** a self-hosted SG/Send is protected by a single access key (`SGRAPH_SEND__ACCESS_TOKEN`) that gates every route — API and reads alike. That key is your deployment's licence and admission ticket in one. Details: [security model](../reference/security-model.md).
