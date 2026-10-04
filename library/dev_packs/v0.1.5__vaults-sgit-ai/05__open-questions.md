# 05 — Open Questions, Decisions, and the Record

Resolve §1 and §2 before step 2 of the plan. §3 is written during the work. Every row keeps its answer and date once given.

---

## 1. Decisions (Dinis)

| # | Decision | Options | Recommendation | Answer / date |
|---|---|---|---|---|
| D1 | Repo | (a) keep `SGit-AI__API`; (b) new `SGit-AI__Vault__API`; (c) rename `SGit-AI__API` → `SGit-AI__Vaults`, holding API + web + deploy | **(c)** — one image ⇒ one release cycle ⇒ one repo (ADR-6); the name follows the product and the domain; rename keeps CI, Pages, the deploy vault | |
| D2 | Python package | `sgit_ai_api` vs `sgit_vaults` (+ `sgit_vaults__ui`) | **`sgit_vaults`** — the rename is the wire change in `/api/info/versions` and the reason for the major bump | |
| D3 | History pointer | wording only (fresh history is decided) | README: "taken from `the-cyber-boardroom/SGraph-AI__App__Send` @ `5d50ae8`; paths in `library/dev_packs/v0.1.5__vaults-sgit-ai/01`" | |
| D4 | Lambda artefact | (a) zip + SnapStart primary; (b) container image everywhere | **(b)** with the cold-start measurement as the gate; zip kept only as an in-repo optimisation if the numbers demand it | |
| D5 | Existing vault data | (a) fresh start; (b) one-time S3 copy at cutover; (c) read-through to the old bucket | **(b)**; old host read-only for a grace period (suggest 90 days) | |
| D6 | Hosted auth | (a) remote lookup → Send Admin (transitional); (b) env single key only; (c) native token registry now | **(a) hosted, (b) self-host** — both exist, zero code; (c) is Explorer's follow-up | |
| D7 | UI clean-up depth | (a) flatten the build output, no component edits; (b) also rename `send-*`, split `sg-send.js` | **(a)** in this pack; (b) as the first post-cutover quality pass | |
| D8 | `__Send`'s joint image (`diniscruz/sg-send-vault`) | retire after cutover; or rebuild from the new package | **retire**; deploy.sgit.ai pages point at the new image | |
| D9 | Domains and the CLI default | `vaults.sgit.ai` (main) + `dev.vaults.sgit.ai` (dev); old hosts 301 `/api/vault/*` for the grace period; CLI default flips in a release | as stated | |
| D10 | Team | Explorer with a Villager label; or restart the Villager team with this pack as its handover brief and a refreshed `.claude/villager/CLAUDE.md` | **restart the Villager team**; its Cartographer owns `maps/vaults-sgit-ai__evolution.mmd` | |

## 2. Questions (need a human action or a product answer)

| # | Question | Why it matters | Default if unanswered | Answer / date |
|---|---|---|---|---|
| Q1 | Are **read-only share tokens** a vault feature? They are transfers (`deriveRoTokenTransferId` → `/api/transfers/download`) and `sgit share` no longer exists in CLI 0.16 | if yes: a vault-scoped snapshot route (new, Explorer) or a transitional proxy to Send; if no: the RO-token path in the web is dead code to record | **no** — record as a Send feature exposed by the vault web; the web keeps calling the Send host for it during the grace period, then the code path is a deletion candidate | |
| Q2 | Are **public previews** (`sg-link-card`, `/api/public-preview/*`) a vault feature? | same shape as Q1 | **no** — same handling | |
| Q3 | **AWS account + region** for the new footprint; who runs the OIDC bootstrap and sets `AWS_DEPLOY_ROLE_ARN` | first live run of any CFN; first Terraform apply | the `__Send` account, `eu-west-2`, Dinis runs the bootstrap once | |
| Q4 | **Image registry**: GHCR under `SGit-AI` or Docker Hub `diniscruz/*` | secrets, org scoping, the README's `docker run` line | **GHCR** (`ghcr.io/sgit-ai/vaults`) — no extra secrets, org-scoped | |
| Q5 | **DNS** for `vaults.sgit.ai`, `dev.vaults.sgit.ai` — and `deploy.sgit.ai`, which still does not resolve | cutover; the deploy docs site | Dinis at the DNS provider; CNAME to CloudFront / Pages | |
| Q6 | **CLI team**: default base URL, drop the `/api/auth/whoami` probe, new `Vaults__Test_Server` import path; status of static transport (`--transport auto` is in the README, not in PyPI 0.16.0) | cutover needs a CLI release | open a thread in `team/comms/briefs/` at step 2 | |
| Q7 | **sgit.ai handover**: `deploy/vault.json` still reads `fyofmkvr` from `dev.send.sgraph.ai`; `ivpijuvg` has never been pushed to a live server; sites embed from `dev.vault.sgraph.ai` | vaults.sgit.ai becomes the live server for the deploy docs; embeds re-point | at step 7: push `ivpijuvg` to vaults.sgit.ai with the escrowed key; update `vault.json` once | |
| Q8 | **Terraform scope**: AWS only (mirror the three CFN shapes) or GCP too | net-new work; README test scope | **AWS only**; Cloud Run stays a documented command | |
| Q9 | **`check-token` indicator** in the vault web (`vault-header`, `vault-settings`, `vault-credentials`) calls a Send route | see `01` §4.1 | keep calling the Send host during the grace period; record `GET /api/info/token` as an Explorer follow-up | |
| Q10 | **Grace period** length for the old host and the redirects | rollback window (`04` §4) | 90 days | |
| Q11 | **The edge 403→404 rewrite.** `dev.send.sgraph.ai`'s CloudFront applies the static site's `403 → /404.html` rule to `/api/*`, so gate failures (wrong write key, wrong enum key, bad append token) reach clients as 404. The parity gate (`tests/regression/`) found it on 4 Oct: in-process 403 vs live 404 on three probes | the new CloudFront for vaults.sgit.ai must **not** carry that rule, or the contract changes at the edge; and the deployed-mode gate must run against the origin (Lambda URL) as well as the edge | new distribution without the custom error response for `/api/*`; gate runs both | |

## 3. The Record (written during the work)

### 3.1 Deletion candidates (record, do not delete)

| Item | Where | Evidence | Series |
|---|---|---|---|
| `mgraph-ai-service-cache`, `-client` | Lambda pins, `DEPENDENCIES__TRACKED`, one constant in `Deploy__Service.py` | imported once, for an env-var name | new repo, step 3 (trim from tracked deps; the constant only matters if the zip path is kept) |
| `APP_SEND__UI__USER__*`, n8n constants | `user__config.py` | Send-only | dropped at step 3 (allowed: not behaviour) |
| `lambda_handler__user.py`, `Deploy__Service.py`, `_for_osbot_aws/*`, `tests/deploy/User__Lambda/*`, `.github/actions/aws__deploy__lambda` | zip deploy path | only if ADR-4's measurement lets the image be the sole artefact | step 8 |
| RO-token and public-preview code paths in the vault web | `vault-loader.js`, `app-shell.js`, `sg-link-card.js`, `public-preview-read.js` | Q1/Q2 = no | step 8 |
| `send-browse` naming, `sg-send.js` transfer calls | vault web `_common` | Send naming inside the vault web | quality pass (D7b) |
| `SEND__*` env names | config, templates, docs | aliases per ADR-7 | later series |
| Vault routes on `dev.send.sgraph.ai`, `deploy-ui-vault.yml`, `diniscruz/sg-send-vault` | `__Send` | after the grace period | `__Send` deletion series |

### 3.2 Defects found, not fixed (Villager rule: behaviour changes go to Explorer)

| # | Where | Finding |
|---|---|---|
| F1 | container CORS re-assert | omits `x-sgraph-vault-enum-key` — cross-origin append list/fetch fail preflight in auth mode |
| F2 | MCP mount | omits `api/vault/append`; never forwards the write key |
| F3 | all token checks | no Admin URL + empty env token = open instance (documented; keep saying so loudly) |
| F4 | `Service__Vault__Pointer` | write-key hash compared with `==`; TOFU on first write |
| F5 | `Storage__Paths` + CloudFront function | S3 root duplicated; env read at import time |
| F6 | append lane | folder named with the raw append token (per `__Send` reality doc, 6 Sep) — migration needed, "Villager/DevOps-coordinated" |
| F7 | `Routes__Vault__Presigned` | uncached token check (an Admin round-trip per call in hosted mode) |

### 3.3 Follow-ups for other teams

| Team | Item |
|---|---|
| Explorer | native token registry (severs D6a); `GET /api/info/token` (Q9); vault-scoped snapshot route if Q1 = yes; F1–F7 |
| CLI | Q6 |
| Villager Cartographer | keep `maps/vaults-sgit-ai__evolution.mmd` current at each step; add the production topology map after step 7 |
| Librarian (both repos) | reality docs at steps 2, 3, 7; `.claude/villager/CLAUDE.md` refresh (D10) |
| wardley-maps.sgit.ai | T2 on its list (fix the 13 broken `.mmd` sources in `__Send`) is unrelated to this pack but the map here follows its rules; offer it as a rendered example once it is stable |

### 3.4 Measurements (fill in)

| Measurement | Baseline (`__Send`) | New | Step |
|---|---|---|---|
| Lambda cold start (zip + SnapStart vs image + LWA) | | | 5 |
| Lambda p50 `/api/vault/read` warm | | | 5 |
| Image size | ~250 MB (joint image) | | 5 |
| Test counts (API / web / conformance / smoke) | 512+9 / … / 5 / 8 | | 3–5 |

*Released under CC BY 4.0.*
