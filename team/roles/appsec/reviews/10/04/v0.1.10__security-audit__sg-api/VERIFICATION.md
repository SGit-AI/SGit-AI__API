# Verification of the 4 Oct 2026 audit — with the pinned dependencies installed

The two audit runs were **source-only** (the skill forbids fetching dependencies), which is why
Run A has zero confirmed records. This session has the exact baseline installed
(`sgraph-ai-app-send` from the git archive of `5d50ae8`, with osbot-utils, osbot-fast-api,
memory-fs, osbot-aws, fastapi-mcp — the same install the parity gate uses), so the audit's own
**bounded local plans** could be run as written: in-memory storage, a scratch temp dir for the
disk backend, loopback only, dummy ids and keys, **no traffic to any deployment**.

Result: **six of the twelve leads are now confirmed**, plus the deploy-lane finding. Nothing here
was reported to or tested against `dev.send.sgraph.ai` or any AWS account.

## Run B — the deploy lane (this repo)

| Finding / lead | Verdict | How | Fix (same commit) |
|---|---|---|---|
| Deploy role can rewrite its own IAM policy → account admin | **Confirmed** by reading the template: `role/sgit-vaults-*` matched `sgit-vaults-github-deploy`, no condition, no boundary | static | One role **per stage** (`sgit-vaults-github-deploy--<stage>`), trust = that stage's Environment subject only; IAM writes allowed only on `role/sgit-vaults-lambda--<stage>` **and only with the permissions boundary `sgit-vaults-lambda-boundary` attached**; `PassRole` only to Lambda; explicit `Deny iam:*` on every deploy role; deny on boundary/policy tampering. `lambda.cfn.yml` sets the boundary on the execution role. Pinned by `tests/unit/deploy/test_deploy_templates.py`. |
| One role for all stages (dev job holds prod authority) | **Confirmed** by reading | static | Same change: per-stage roles with stage-scoped stack / function / bucket / role ARNs. CloudFront and Route53 stay account-wide (no resource scoping exists) and the README says so. |
| Prod dispatch inputs interpolated into the credentialed shell | **Confirmed**: the audit's quote-breakout fixture printed its marker against the old step; against the new step the payload reaches `aws` as one argument and the marker does not print | local fixture | Every input and secret reaches `run:` through `env:`; pinned by test (`no_input_or_secret_is_interpolated_into_shell_text`). |
| Following the README leaves prod open while the pipeline stays green | **Confirmed** by reading GitHub's rules: Environment secrets do not resolve in a reusable-workflow caller job without an environment, so the README's instruction produced an empty token and the old step only warned | static | Callers use `secrets: inherit`; the one Environment-bound job reads `SGIT_VAULTS__ACCESS_TOKEN`; an empty token **fails the deploy** unless `open_instance=true` was passed on purpose. Smoke, parity and the CloudFront check now run inside that same job, so prod's reviewers approve once and the token never leaves the Environment. |
| `cloudfront` job assumed the role without `environment:` (would fail closed) | **Confirmed** by reading | static | Folded into the Environment-bound job as the last step. |
| `id-token: write` workflow-wide; unpinned OSBot action | noted | — | `id-token: write` is now on the deploy job only. The `@dev` action ref is the house convention across the origin repo's pipelines; left as is, listed here. |
| `s3:Put*` on stage buckets (bucket policy / ACL / public-access) | **Confirmed** by reading | static | Bucket statement is now an explicit create/configure list; no object actions, no policy/ACL/BPA writes. |
| Token in plaintext Lambda env; base images by tag; no tarball digest | noted, unchanged | — | Phase-2 vault services (secrets as ciphertext) is the designed answer for the first; the other two are hardening for the move. |

## Run A — the extraction set (origin `5d50ae8`, the code this lane serves today)

| # | Lead | Verdict | What was observed (bounded, in-memory / temp dir, dummy data) |
|---|---|---|---|
| 1 | Presigned download-url bypasses expiry and `max_downloads` | **Confirmed** | Expired transfer with `max_downloads=1`: the direct path returns `410 expired`; `create_download_url` returned a presigned GET **twice**, `download_count` climbed to 2, status stayed `completed`. (S3 signer replaced by an `S3` subclass whose `create_pre_signed_url` returns a string; no AWS.) |
| 2 | Presigned upload-url lets any token holder overwrite or resurrect transfers | **Confirmed** | Completed transfer → `delete_transfer` with the right auth → status `deleted`, payload gone. `create_upload_url` still returned a presigned PUT; after writing bytes, `complete_transfer` returned ok and status became `completed` again; the presigned download then served it. |
| 3 | Unvalidated vault `file_id` allows `..` escape | **Confirmed on the disk backend; harmless-literal on memory (and by construction on S3)** | `Safe_Str__File__Path('a/../b')` keeps `..`. On `Storage_FS__Local_Disk` in a temp dir: an **anonymous** `batch_read('aaaa1111', [{'file_id': '../../bb/bbbb2222/bare/refs/ref-main'}])` returned the other vault's bytes, and a write batch from a freshly claimed vault **overwrote** them (victim bytes became the attacker's). On `Storage_FS__Memory` the same key is stored literally and the read returns `not_found`. Disk is the default of the origin's EC2 template **and of this repo's Docker image** (`SEND__STORAGE_MODE=disk`); the Lambda lane deploys with S3. |
| 4 | Append lane authorises from a stale cache after destroy | **Confirmed, single warm process, both variants** | Full app in-memory via TestClient. Write → configure anchors → append (200) → destroy (200) → the pointer lane now refuses the old key (403) but **append with the old token still returns 200**. Re-claim variant: purge-destroy, new owner claims with K2 → configure with the **new** owner's key is **403**, configure with the **old** owner's key is **200**. |
| 5 | Pointer manifest cache never revalidated across warm instances | **Confirmed** (two service instances on one store) | A and B share one `Storage_FS__Memory`. A destroys with K1; B still accepts K1 for writes. After purge + re-claim with K2 on A: B accepts K1 and **rejects K2**. Needs more than one warm Lambda environment, which the User Lambda has (no reserved concurrency). |
| 6 | Raw access token interpolated into the admin lookup path | **Confirmed end to end on loopback** | The decisive library fact: `requests` normalises dot-segments (`/tokens/lookup/../../rooms/lookup/abc` is sent as `/rooms/lookup/abc`), and `Fast_API__Client__Requests.execute_remote` builds `f"{base_url}{path}"` over a `requests.Session`. With the admin app on `127.0.0.1` behind uvicorn, one dummy room created, and `Service__Access_Token` in REMOTE mode: `check('nope')` → 401; `check('../../rooms/lookup/<room_id>')` → **passes the gate**. REMOTE is the production mode. Any admin GET that returns `status: active` for an id the caller knows (rooms, invites, keys) is a valid "access token". The transfers routes are safe (they sanitise with `Safe_Str__Id`); the vault pointer, append, presigned and vault-presigned copies are not. |
| 7 | og-image serves an author-chosen Content-Type | Confirmed by reading (not run) | `thumbnail_bytes` returns `m.group(1)` from `^data:([^;]+);base64,` and the route passes it as `media_type`; Starlette does not filter media types. Impact depends on same-origin UI deployment, as the audit says. |
| 8 | Cold-start dependency zip from S3 without owner pin / digest | not run | Deployment fact (bucket ownership per region). Hardening stands. |
| 9 | Unescaped signup fields in the HTML operator email | not run | Depends on the n8n send step. Fix is `html.escape`; trivial, do it in the move. |
| 10 | Concurrent downloads exceed `max_downloads` | not run | Dominated by lead 1 on S3 deployments. |
| 11 | PBKDF2 600k on every anonymous preview call | not run | Resource exhaustion; needs WAF / caching facts. |
| 12 | Two n8n sends per anonymous signup | not run | Operator-spend; needs quota facts. |

### What this means for the refactoring

- Leads **3, 4, 5 and 6 are vault-API defects** and move with the code. The vaults.sgit.ai pack's
  rule is "move with zero changes, verify with the identical-output test, change afterwards":
  the parity gate will faithfully carry these over, so they go on the **step 1.4+ fix list**, each
  with the fixture above turned into a test that fails on the baseline and passes after the fix.
  The smallest fixes are the audit's: one `file_id` validator mirroring
  `Safe_Str__Vault__Append__File_Id` at the pointer-service entry points; one shared manifest
  cache with a short TTL, invalidated by `delete_vault` for both services and re-read on any key
  mismatch; token validation `^[A-Za-z0-9_-]{1,64}$` plus `token_name` equality in the gate,
  with the four copies collapsed into `Service__Access_Token`.
- Leads **1 and 2 are Send (transfers) defects**, which stay in the origin repo by decision; they
  are reported here because the extraction set still carries the transfer routes until step 1.3
  deletes them from this side.
- **Lead 6 and lead 3 are live today** in the origin's deployed API (lead 6 wherever the admin
  lookup is configured; lead 3 wherever storage is on disk). Both are the origin repo's to fix;
  this document is the reproduction. No request was made to any live endpoint.
- This repo's **Docker image defaults to `SEND__STORAGE_MODE=disk`** and therefore inherits lead 3
  as soon as that image serves more than one vault owner. The Lambda lane (S3) does not.

### Fixtures

The exact scripts are in the session transcript; each is under 40 lines, uses only the
in-memory stack, a temp dir, or loopback, and will be turned into regression tests in the
move (`tests/regression/` is the natural home, next to the parity scenarios, so each fixture
runs against both legacy and new).
