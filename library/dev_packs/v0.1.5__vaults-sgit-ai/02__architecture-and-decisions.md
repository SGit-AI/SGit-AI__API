# 02 — Architecture and Decisions

The target shape and the ADRs it rests on. ADR-1..5 must be settled (Dinis, `05`) before step 2 of the plan; ADR-6..9 are executed during the work.

---

## 1. Target Repository Layout (PROPOSED)

```
SGit-AI__Vaults/                          (name per D1)
├── README.md                              the README test starts here: Docker in 60s → sgit clone → open in browser
├── sgit_vaults/                           (package per D2)
│   ├── api/            Fast_API__Vaults, routes/{Routes__Vault, Routes__Vault__Append, Routes__Vault__Presigned, Routes__Info}
│   ├── services/       Service__Vault__{Pointer,Append,Presigned,Zip}, Service__Access_Token, token_lookup/ (remote client)
│   ├── storage/        Vaults__Config, Enum__Storage__Mode, Storage_FS__{S3,Local_Disk}, Storage__Paths
│   ├── schemas/        Safe_Str__Vault__Append*, Schema__Vault__Presigned
│   ├── crypto/         Vault__Crypto (Python reference for the JS derivation)
│   ├── mcp/            MCP__Setup
│   ├── container/      Fast_API__Vaults__Container, Routes__Auth__Login, TLS launcher, serve.py, app.py
│   ├── testing/        Vaults__Test_Server (the harness the CLI's tests use)
│   └── version
├── sgit_vaults__ui/                       one flat tree (the flattened v0.2.3): index.html, en-gb/, _common/, i18n/, build/
├── deploy/
│   ├── docker/         Dockerfile (no overlay step), compose example
│   ├── aws/cfn/        lambda, ec2, ecs-fargate, ami-pipeline, github-oidc-role
│   ├── aws/terraform/  modules mirroring the three CFN shapes (new)
│   ├── gcp/            cloud-run.md + the gcloud command
│   ├── heroku/         app.json, heroku.yml
│   └── static-hosting/ the projection recipe (what deploy.sgit.ai already does)
├── docs/               self-host/, protocol/, api/, operations/  (source; vault/ is the published form)
├── vault/              the deploy-docs vault (ivpijuvg) — already here
├── pages/              deploy.sgit.ai shell — already here
├── tests/
│   ├── unit/           api (in-memory, no mocks), storage, crypto, mcp, container
│   ├── ui/             jsdom unit, loader integration, Playwright e2e, browser integration (sgit round-trip)
│   ├── conformance/    the static-read suite — already here
│   └── deploy/         smoke suite vs any target (SG_BASE_URL)
├── .github/workflows/  ci-pipeline (tests → tag), build-image, deploy-full-cycle, deploy-vault-pages, _test-ui
└── team/, library/     this repo's own records (already here)
```

## 2. Deployment Topology (PROPOSED)

```
                         ┌──────────── one image: ghcr.io/sgit-ai/vaults:{version} ────────────┐
                         │  python:3.12-slim · uvicorn · LWA extension · sgit_vaults + __ui       │
                         │  /            → vault web (StaticFiles)                                │
                         │  /api/*       → FastAPI                                                 │
                         │  /auth/*      → single-key login page                                   │
                         └───────────────┬───────────────┬────────────────┬────────────────────────┘
                                         │               │                │
              ┌──────────────────────────▼───┐   ┌───────▼────────┐   ┌───▼──────────────────────┐
              │ docker run  (laptop, air-gap) │   │ Lambda (image)  │   │ Fargate / EC2 / Cloud Run │
              │ memory | disk | s3            │   │ Function URL    │   │ ALB / caddy / $PORT       │
              └──────────────────────────────┘   │ + CloudFront    │   └──────────────────────────┘
                                                 │ s3 | memory     │
                                                 └───────┬────────┘
                                                         │
   hosted:  dev.vaults.sgit.ai (dev branch) · vaults.sgit.ai (main) — CloudFront → Lambda URL; immutable objects → S3 direct
   storage: {account}--sgit-vaults--{region}, root  sgit-vaults/v1/   (D5)
   auth:    env single key (self-host) | remote token lookup → Send Admin (hosted, transitional; D6)
```

What is deliberately **not** in the topology: a second artefact (the zip Lambda) unless D4 keeps it as an optimisation; any call from the vault service to Send other than the transitional token lookup; the Send UIs.

---

## ADR-1: The boundary is the vault product — ACCEPTED (memo)

`sgit_vaults` = vault API (pointer, append, presigned, info, MCP) + vault web + deploy + docs. Not transfers, not Send UIs, not the Admin Lambda. Supersedes the August ADR-1 ("the User Lambda's reachable set"), which was a *move* boundary; this is a *product* boundary.

**Cost:** two vault-web features are transfer-backed (share tokens, public previews) and one indicator uses a Send route (`check-token`). They are Q1/Q2 — product calls, not engineering ones. Everything else cuts clean (verified: the vault families are 28 OpenAPI paths and their services import nothing from transfers).

## ADR-2: Names follow the product; the rename is the major bump — PROPOSED (D1, D2)

Repo `SGit-AI__Vaults` (rename of `SGit-AI__API`, keeping CI, Pages, the deploy vault), package `sgit_vaults`, image `ghcr.io/sgit-ai/vaults`, hosts `vaults.sgit.ai` / `dev.vaults.sgit.ai`, AWS names `sgit-vaults-*`.

**The one wire change** this causes: `/api/info/versions` keys the app version by package name. The CLI does not parse that key; the smoke suite does (update it). Everything else on the wire is verbatim. Per the August ADR-7, the *rename* is the reason for a major version, not the move.

**Why not a separate `Vault__API` repo:** the memo's own criterion — one image with UI and API — means they always ship together, and ADR-6 (release cycles, not concepts) says one repo. `SGit-AI__API` was named when the plan was "API only"; the memo widened it.

## ADR-3: Fresh history; `__Send` is the archive — ACCEPTED (memo)

The new repo starts at commit 1. The README records the `__Send` commit the code was taken from (`5d50ae8`) and the paths, so `git log --follow` in `__Send` answers "why is this line here". This dissolves the August blocker (shallow clones) entirely.

**Cost:** blame/bisect across the boundary needs two repos. Acceptable and stated.

## ADR-4: One artefact: the container image, for every target including Lambda — PROPOSED (D4)

The image already carries the Lambda Web Adapter and the CFN `lambda.cfn.yml` already deploys it. Making it the *only* artefact gives the README test one thing to build and one thing to deploy.

**Gate before cutover:** cold start and p50 on the image-based Lambda vs today's zip + SnapStart, measured with the smoke suite. If materially worse, keep the zip deployer *in the same repo* as an optimisation for the hosted stage, documented as such. Never as a second product.

## ADR-5: Data moves by copy at cutover; the path root changes at the boundary — PROPOSED (D5)

New bucket, new root (`sgit-vaults/v1/`). Existing vaults are copied once from `__Send`'s bucket (`…/shared/vault/` prefix) at cutover; the old host stays up read-only for a grace period. Because vault ids and keys are client-derived, a copied vault opens unchanged at the new host — no client migration.

**Why not read-through to the old bucket:** it is the coupling we are removing. **Why change the root at all:** the current root encodes `sg-send` twice; the README test should not ask a stranger to type it.

## ADR-6: Auth by configuration, registry later — PROPOSED (D6)

`Service__Access_Token` already has two modes. Self-host = env single key (`SGRAPH_SEND__ACCESS_TOKEN`, aliased per ADR-7). Hosted = remote token lookup, pointed at Send's Admin Lambda as a **declared, transitional** dependency. A native token registry in the vault API is the Explorer follow-up that severs it; it is a feature and does not belong in a Villager pack.

## ADR-7: Environment variable names keep working; new names are aliases — PROPOSED

`SEND__STORAGE_MODE`, `SEND__S3_BUCKET`, `SEND__DISK_PATH`, `SGRAPH_SEND__ACCESS_TOKEN`, `SEND__STORAGE_{BASE,VERSION}`, `SEND__DEPLOYMENT_ID` are read by every deploy template, the CFN parameters, the Docker README, the deploy vault and the CLI docs. Renaming them is a behaviour change for operators. This pack **adds** `VAULTS__*` equivalents read first, keeps the old names as fallbacks, and documents only the new ones. Removal is a later series.

## ADR-8: The vault web is flattened, not edited — PROPOSED (D7)

Commit what `build-vault-static.sh` produces with `VAULT_DEFAULT_ENDPOINT=""` as the source tree. That single act removes the IFD overlay stack, the user-UI layer merge, the CDN patching and the hard-coded endpoint — without touching a component. The e2e and unit suites prove parity. Component renames (`send-browse` → `vault-browse`), the `sg-send.js` split, and dead-code removal inside components are the first post-cutover quality pass, when parity is already proven and the suites are the safety net.

## ADR-9: Docs are the deliverable; the deploy vault is their published form — ACCEPTED (memo + `MAINTENANCE.md`)

`docs/` in the repo is the source; `vault/` (ivpijuvg, projected to deploy.sgit.ai) is re-generated from it in the same commit. The README test is run by a person or a fresh session with no access to `__Send`.

---

## 3. What the Evolution Map Says (see `maps/vaults-sgit-ai__evolution.mmd`)

The transformation moves five components from custom-built to product — auth (decoupled), vault web (flattened, same-origin), deploy artefacts (one image, CFN run live, Terraform born), docs (README test), the static-read projection (a documented target) — and retires one (the zip deploy as a product). It moves nothing that is already product (protocol, read contract, storage, CLI). That is the whole job, stated on one axis.

*Released under CC BY 4.0.*
