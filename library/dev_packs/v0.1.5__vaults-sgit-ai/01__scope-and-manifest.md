# 01 — Scope and Manifest

**The rule (from the memo):** the vault, and only the vault — API, web, deploy, docs — as one product at vaults.sgit.ai. Send stays where it is.

Everything below is measured against `__Send` dev @ `5d50ae8` (v0.33.69). Re-run the commands in §6 before trusting it.

---

## 1. What Moves — and how it is transformed on the way

### 1.1 Vault API (Python)

| From (`sgraph_ai_app_send/…`) | To (`sgit_vaults/…`, name per D2) | Transformation allowed |
|---|---|---|
| `lambda__user/fast_api/Fast_API__SGraph__App__Send__User.py` | `api/Fast_API__Vaults.py` | rename; register only vault routes (§1.1a); drop Send service wiring |
| `lambda__user/fast_api/routes/Routes__Vault__Pointer.py` | `api/routes/Routes__Vault.py` | rename only; `tag` stays `api/vault` |
| `lambda__user/fast_api/routes/Routes__Vault__Append.py` | `api/routes/Routes__Vault__Append.py` | none |
| `lambda__user/fast_api/routes/Routes__Vault__Presigned.py` | `api/routes/Routes__Vault__Presigned.py` | none |
| `lambda__user/fast_api/routes/Routes__Info__SGraph.py` | `api/routes/Routes__Info.py` | rename; `versions()` key becomes the new package name (ADR-2, the one wire change); `DEPENDENCIES__TRACKED` minus `mgraph-ai-service-cache*` |
| `lambda__user/service/Service__Vault__Pointer.py`, `Service__Vault__Append.py`, `Service__Vault__Presigned.py`, `Service__Vault__Zip.py`, `Service__Access_Token.py` | `api/services/…` | rename only |
| `lambda__user/service/Admin__Service__Client*.py` (3 files) | `api/services/token_lookup/…` | keep as the *remote token lookup* client (D6a); rename to say what it is |
| `lambda__user/storage/Send__Config.py`, `Enum__Storage__Mode.py`, `Storage_FS__S3.py`, `Storage_FS__Local_Disk.py`, `Storage__Paths.py` | `storage/…` | rename `Send__Config` → `Vaults__Config`; env var names **unchanged** (`SEND__STORAGE_MODE`, …) in this pack — see ADR-7 for the alias plan; `Storage__Paths` keeps only the vault path functions; root default per D5 |
| `lambda__user/schemas/Safe_Str__Vault__Append*.py`, `Schema__Vault__Presigned.py` | `schemas/…` | none |
| `lambda__user/user__config.py` | `config.py` | keep header constants and env var names verbatim; drop `APP_SEND__UI__USER__*`, n8n, `APP__SEND__USER__LAMBDA_DEPENDENCIES` becomes the image's `requirements.txt` (D4) |
| `utils/Vault__Crypto.py`, `utils/MCP__Setup.py`, `utils/Version.py` | `crypto/`, `mcp/`, `utils/` | none (`Vault__Crypto` moves although only its test uses it — it is the Python reference for the JS derivation and belongs with the protocol) |
| `lambda__user/lambda_function/lambda_handler__user.py` | `lambda_handler.py` | keep only if D4 keeps a zip path; otherwise the container image's LWA is the Lambda entry and this file is a deletion candidate |
| `lambda__user/lambda_function/deploy/Deploy__Service.py`, `_for_osbot_aws/*` | `deploy/aws/lambda_zip/` | same condition as above |
| `lambda__user/testing/Send__User_Lambda__Test_Server.py` | `testing/Vaults__Test_Server.py` | rename; it is the harness external projects (the CLI) use — announce the new import path |

**1.1a Routes registered on the new app (the contract):** `Routes__Info`, `Routes__Vault`, `Routes__Vault__Append`, `Routes__Vault__Presigned`, MCP mount (`include_tags` = `api/vault`, `api/vault/presigned`, and — fix recorded, not applied — `api/vault/append`). CORS allow-list verbatim from today, **minus nothing** (keep `x-sgraph-transfer-delete-auth` out only if Q1/Q2 confirm no transfer routes come along).

**Not moving from the User Lambda:** `Routes__Transfers`, `Routes__Presigned`, `Routes__Early_Access`, `Routes__Public_Preview`, `Routes__Join`, `Transfer__Service`, `Service__Presigned_Urls`, `Service__Early_Access`, `Public_Preview__Service`, `Schema__Transfer*`, `Schema__Presigned`, `Schema__Early_Access`, `Transfer_Id`, `Enum__Transfer__Status` — unless Q1/Q2 pull `download`/`info` across as a vault snapshot route.

### 1.2 Vault web (static)

| From | To (`sgit_vaults__ui/`) | Transformation |
|---|---|---|
| `sgraph_ai_app_send__ui__vault/v0/v0.2/v0.2.3/` (178 files) **as flattened by** `scripts/build-vault-static.sh` with `VAULT_DEFAULT_ENDPOINT=""` | one flat tree: `index.html`, `en-gb/…`, `_common/…`, `i18n/…` | **commit the build output as the source** (D7a). The overlay stack (`_common` from user UI v0.3.0–v0.3.3), the CDN URL patching and the endpoint rewrite all disappear as steps because their *result* is what is committed |
| `scripts/generate_vault_i18n_pages.py` | `sgit_vaults__ui/build/generate_i18n_pages.py` | none; runs in CI as today |
| `scripts/inject_build_version.py` (build-info.js) | `sgit_vaults__ui/build/` | none |
| older vault UI versions `v0.1.x`, `v0.2.0–v0.2.2` | **do not move** | archived in `__Send` |

### 1.3 Tests

| From | To | Note |
|---|---|---|
| `tests/unit/lambda__user/{fast_api/routes/test_Routes__Vault__*, service/test_Service__Vault__*, storage/*, fast_api/test_Fast_API__…, fast_api/test_MCP__Mount__User, lambda_function/*, testing/*}` | `tests/unit/api/…` | import paths change; assertions do not. Route-list assertion in `test_Fast_API…` shrinks to the vault families — that shrink *is* the boundary, review it line by line |
| `tests/unit/utils/*` (incl. `test_vault_crypto_interop.js`), `tests/unit/_for_osbot_aws/*` (if D4 keeps zip) | `tests/unit/…` | |
| `tests/unit/vault_ui/*`, `tests/integration/vault_ui/{loader,live,browser}`, `tests/e2e/vault_ui/*` (13 Playwright specs incl. `test__sgit_round_trip.py`) | `tests/ui/…` | these are the **parity proof for the web**; `package.json` scripts `test:vault-*` and `_test-ui-vault.yml` come with them |
| `tests/deploy/targets/test_smoke__deployed_target.py` | `tests/deploy/` | `test_3__vault_ui_root` now holds (UI ships in the image); `test_2` asserts the new package name |
| `tests/unit/lambda__user__with_admin/*` | **stay** in `__Send` | cross-lambda; the remote-lookup client is covered by the env-mode tests + one live smoke |

### 1.4 Deploy

| From | To (`deploy/`) | Transformation |
|---|---|---|
| `sgraph_ai_app_send__docker/{Dockerfile, serve.py, app.py, Fast_API__SGraph__Send__Container.py, Routes__Auth__Login.py, Fast_API__TLS__Launcher.py, Schema__Fast_API__TLS__Config.py}` | `deploy/docker/` + `sgit_vaults/container/` | Dockerfile loses the overlay build step (copies `sgit_vaults__ui/` as is); container app renames; login page text |
| `deploy/aws/{lambda,ec2,ecs-fargate,ami-pipeline,github-oidc-role}.cfn.yml` + `README.md` | `deploy/aws/cfn/` | names `sg-send-*` → `sgit-vaults-*`; image URI; nothing structural |
| `.github/workflows/deploy-full-cycle.yml` | `.github/workflows/deploy-full-cycle.yml` | image name, stack prefix, `AWS_DEPLOY_ROLE_ARN` |
| `app.json`, `heroku.yml` | `deploy/heroku/` | names |
| **new** | `deploy/aws/terraform/` | modules mirroring the three CFN shapes (Q8) |
| `.github/actions/aws__deploy__lambda`, `tests/deploy/User__Lambda/*` | only if D4 keeps zip | |
| `deploy-ui-vault.yml` (S3 + CloudFront for dev.vault.sgraph.ai) | **does not move** | the UI ships in the image; a static-UI-only deploy is a later option, not this pack |

### 1.5 Docs (the product, per the memo)

New, written in this repo, in this order of importance: `README.md` (quickstart: Docker in 60 seconds → `sgit clone … --endpoint`), `docs/self-host/` (one page per target, lifted from the deploy vault and made true), `docs/protocol/` (the read contract, derivations, cache semantics — already written in `vault/docs/`), `docs/api/` (generated `openapi.json` + the header table), `docs/operations/` (storage modes, config reference, backup/restore, rotation). The deploy vault (`vault/`) keeps being the *published* form; the repo `docs/` is the source (`MAINTENANCE.md` already says docs move with code).

---

## 2. What Stays in `__Send` (explicitly)

| Stays | Why |
|---|---|
| `lambda__admin/` (74 files), all Send UIs (`__ui__user`, `__ui__share`, `__ui__open`, `__ui__workspace`, `__ui__admin`), `sgraph_ai__website/` | not vault |
| transfers / presigned / early-access / public-preview routes and services | "keep the send stuff where it is" |
| the User Lambda as deployed (`sgraph-ai-app-send--user--{stage}`) | keeps serving Send **and** `/api/vault/*` until cutover (step 7), then vault routes 301 for a grace period (D9) |
| `diniscruz/sg-send-vault` image | until D8 |
| older vault UI versions, the overlay build script, `deploy-ui-vault.yml` | archive |
| `library/`, `team/`, briefs, reality docs | archive + pointer; this repo's own `team/` records the transformation |

---

## 3. The Five Couplings to Sever (each has a home in `05`)

| # | Coupling | Where | Severed by |
|---|---|---|---|
| C1 | Hosted auth calls the Send Admin Lambda for token lookup | `Service__Access_Token`, `Admin__Service__Client__Setup` | D6: config (remote mode stays, pointed at Send transitionally; env single-key for self-host); native registry later |
| C2 | Read-only share token = a transfer | `vault-loader.js:157`, `app-shell.js:1169` | Q1: product decision |
| C3 | Public preview = a transfer | `sg-link-card.js`, `public-preview-read.js` | Q2: product decision |
| C4 | UI defaults to `https://dev.send.sgraph.ai` | 8+ files | D7a: flattened source is same-origin |
| C5 | S3 path root `sg-send__data/sg-send-api__v1.0/shared/` and its duplicate in the CloudFront function | `Storage__Paths.py`, `cloudfront/imm-object-rewrite.js` | D5: new bucket + new root at deploy time; edge function rewritten with it |

Plus one *reverse* coupling that does not block us but blocks `__Send`'s later deletion: `Fast_API__SGraph__App__Send__Admin.py:2` imports `Routes__Info__SGraph` from the user tree.

---

## 4. Ambiguities Found (decide, don't improvise)

1. **`check-token` in the vault web** (`vault-header.js`, `vault-settings.js`, `vault-credentials.js`) calls `/api/transfers/check-token/{name}` to show whether the user's access token is valid. It is a Send route. Options: (a) keep calling the Send host for it (coupling); (b) add `GET /api/info/token` to the vault API that answers from `Service__Access_Token` (small new route — Explorer); (c) drop the indicator. Record under Q1.
2. **MCP** today forwards only the access token, never the write key, and omits append routes. Parity means moving it as is; the fix is recorded, not applied.
3. **Container CORS** omits the enum-key header (found in this morning's review). Same: move as is, record.

---

## 5. Sizing (for the plan)

| Part | Size | Nature of work |
|---|---|---|
| API | ~30 `.py`, ~3,500 lines | mechanical: rename, re-wire, trim |
| Web | 178 + 108 overlaid files, ~34k lines JS | mechanical: flatten, commit, delete build machinery; **no edits inside components** |
| Tests | 27 + 5 + ~20 files, 512 + ~300 tests | import-path edits; route-list assertion edit |
| Deploy | 7 CFN/Docker files + 1 workflow + Terraform (new) | rename + one new module set |
| Docs | new | the real work of the README test |

---

## 6. Verification Commands (re-run first)

```bash
# the vault families on the live app (expect 28 + 7 unlisted = the contract)
SEND__STORAGE_MODE=memory python3 -c "
from sgraph_ai_app_send.lambda__user.fast_api.Fast_API__SGraph__App__Send__User import Fast_API__SGraph__App__Send__User as A
a=A(); a.setup(); p=a.app().openapi()['paths']
print(sum(x.startswith('/api/vault') or x.startswith('/api/info') for x in p), 'of', len(p))"

# what the CLI consumes (expect 12 vault paths + /api/info + the whoami probe)
grep -rhoE "/api/[a-z0-9_/-]+" $(python3 -c "import sgit_ai,os;print(os.path.dirname(sgit_ai.__file__))") | sort -u

# the vault web's Send couplings (expect the RO-token, check-token and public-preview call sites only)
grep -rn "api/transfers" sgraph_ai_app_send__ui__vault/v0/v0.2/v0.2.3 --include='*.js' | grep -v "lib/sg-send/sg-send.js"

# the flattened web tree the new repo will commit
VAULT_DEFAULT_ENDPOINT="" bash scripts/build-vault-static.sh /tmp/vaults-ui && find /tmp/vaults-ui -type f | wc -l
```

*Released under CC BY 4.0.*
