# Security audit: SG/API extraction set (run 1)

## 1. Run profile and limits

| | |
|---|---|
| Target | `the-cyber-boardroom/SGraph-AI__App__Send` @ `5d50ae83`: the extraction baseline pinned by SGit-AI__API's parity gate and deploy lane |
| Profile | **standard, scoped**. This is a partial pass, not complete coverage |
| Scope | `sgraph_ai_app_send/__init__.py`, `lambda__user/` (minus `Routes__Join.py`, which is excluded from the move), `utils/`, `_for_osbot_aws/`. This is the extraction set per `library/dev_packs/v0.33.59__sgit-api-extraction/01__scope-and-manifest.md` |
| Out of scope | `lambda__admin/` (read only as context for one lead), the UI trees, `Routes__Join.py`, and the Docker container app |
| Budget | 30 agent invocations; **28 spent**:<br>• 4 reconnaissance<br>• 8 hunters (7 in wave 1, 1 in wave 2)<br>• 2 post-wave critics<br>• 8 candidate verifiers (Phase 3)<br>• 6 record verifiers (Phase 5) |
| Grouping | Related candidates were grouped per verifier to fit the budget. Each verifier was independent of the hunters, and Phase 3 and Phase 5 were always different agents. This is a deviation from one-verifier-per-candidate. |
| Execution | **Source-only.** The target's runtime dependencies (osbot-utils, osbot-fast-api(-serverless), memory-fs, fastapi-mcp, osbot-aws) are not installed, and the skill forbids fetching them. No target code ran.<br>The only fixtures were stdlib scripts that imported nothing from the target (for example, normalising the key that `Storage__Paths` composes), run under `unshare -rn env -i timeout prlimit`. No artifacts were promoted. |
| Prior runs | None |

**What "source-only" means for the verdicts.** Every lead below stops at a fact that lives in an uninstalled library (how Memory-FS joins paths, how Type_Safe handles defaults, how osbot-aws presigns URLs) or in deployment config (storage mode, concurrency, edge headers, how tokens are issued). The skill does not allow those facts to be assumed, so **this run has zero `confirmed` records**. That reflects the evidence bar, not a clean bill of health.

The fastest way to promote or reject most of these leads is a re-run with the pinned dependencies available offline. Every lead has a bounded local plan for that.

## 2. Posture

Several things are sound:
- The core zero-knowledge design is intact: the server stores ciphertext, and the keys are client-side.
- The `vault_id` and append-lane identifiers are tightly typed.
- Write-key checks are present on every mutating vault route.

The weak spots are **parallel paths and caches that drift from the primary control**:
- The presigned transfer routes skip lifecycle checks that the direct routes enforce.
- The vault pointer service never validates `file_id`, while the sibling append service does.
- The four copies of the access-token check normalise the token differently.
- The ownership caches are never invalidated across service instances or processes.

The fixes are mostly small and local.

## 3. Confirmed findings

None. See section 1 for why.

## 4. Needs validation (no severity; leads, not confirmed vulnerabilities)

Ordered by the parent's view of likely impact if the blocker resolves unfavourably.

| # | Lead | Key trace | Exact blocker | Bounded next step |
|---|---|---|---|---|
| 1 | **Presigned download-url bypasses expiry and max_downloads.** It is unauthenticated and never triggers auto_delete | `Routes__Presigned.py:142` → `Service__Presigned_Urls.py:198,202,213` (direct path enforces `Transfer__Service.py:153,157,169`) | Production in S3 mode; osbot-aws presign | In-memory transfer plus a stub S3: an expired, `max_downloads=1` transfer still yields URLs and the count climbs to 2 |
| 2 | **Presigned upload-url has no pending check.** Any token holder can overwrite a completed transfer, and `complete` brings deleted or exhausted transfers back | `Routes__Presigned.py:127` → `Service__Presigned_Urls.py:232,237` → `Transfer__Service.py:112` | S3 mode; presign semantics; how tokens are issued | Delete a transfer, call `create_upload_url`, write bytes, call `complete` → status is `completed` |
| 3 | **Unvalidated vault `file_id` allows `..` escape** from the vault namespace, cross-vault and into transfers. The read-only batch is anonymous | `Routes__Vault__Pointer.py:167,183` → `Service__Vault__Pointer.py:173,44` → `Storage__Paths.py:34` | `Safe_Str__File__Path` and Memory-FS `Local_Disk` path handling. **The EC2 template defaults to `disk`** (`deploy/aws/ec2.cfn.yml:42`) | `batch_read('aaaa1111', [{'file_id':'../../bb/bbbb2222/…'}])` on `Storage_FS__Local_Disk` in a temp dir |
| 4 | **Append lane authorises from a stale cache after vault destroy.** Old append tokens keep writing, and after a purge and re-claim the old owner keeps configure/purge rights. Needs only **one** warm process | `Routes__Vault__Pointer.py:270` → `Service__Vault__Pointer.py:217,221` while `Service__Vault__Append.py:43,58` → `:139` | Type_Safe per-instance dicts; Memory-FS semantics | Destroy a vault, then append with the old token → expect 403, vulnerable if 200 |
| 5 | **Pointer manifest cache is never revalidated.** The old write key keeps write, delete and destroy rights on other warm instances | `Service__Vault__Pointer.py:51,71,91` | Multiple concurrent warm environments | Two service instances on one store: destroy via A, then write via B |
| 6 | **Raw access token is interpolated into the admin lookup path.** The check accepts any admin JSON with `status: active` | `Service__Access_Token.py:40,44` → `Admin__Service__Client.py:24` | osbot-fast-api REMOTE dot-segment handling; admin front-door routing | Loopback admin app plus `check('../../rooms/lookup/<id>')` |
| 7 | **og-image serves an author-chosen Content-Type** (`text/html`) from the API origin | `Routes__Public_Preview.py:49,54` ← `Public_Preview__Service.py:163` | Whether the API and UI share an origin; edge headers; Starlette | TestClient returns `media_type='text/html'` |
| 8 | **Cold start loads a dependency zip from a predictable S3 name** with no owner pin or digest | `lambda_handler__user.py:12` → `Lambda__Dependencies__Loader.py:84,89,96,99` | Bucket ownership in every region; writers of the key | `head-bucket --expected-bucket-owner` in each region |
| 9 | **Unescaped anonymous signup input** goes into the HTML operator email | `Routes__Early_Access.py:20` → `Service__Early_Access.py:31,69` | Whether n8n/WorkMail sends the body as HTML | Copy `build_email_body` into a stdlib script |
| 10 | **Concurrent downloads can exceed max_downloads** (non-atomic counter) | `Transfer__Service.py:145,157,165,167` | Concurrency and the storage write semantics | A barrier between load and save |
| 11 | **Anonymous `/public-preview/info` runs PBKDF2 at 600k iterations** on every call | `Routes__Public_Preview.py:56,62` → `Public_Preview__Service.py:40` | WAF, caching, reserved concurrency | Time `pbkdf2_hmac` locally |
| 12 | **Anonymous signup triggers 2 n8n sends per request** with no rate limit | `Service__Early_Access.py:44,74` | Upstream rate limits; n8n quota | Owner checks the quota and WAF |

Full traces, evidence and plans for all twelve are in `NEEDS-VALIDATION.md`.

**Rejected (retained so future runs do not repeat it):** `presigned-multipart-declared-size-unbound`. The trace is accurate, but the actor is the authorised uploader the token check exists to admit, and the direct write path already allows unlimited storage. It is moved to hardening.

## 5. Smallest fixes (for owners; no code was changed by this audit)

- **Transfers:**
  - Route `create_download_url` through the same predicates as `get_download_payload`. One shared `_check_downloadable(meta)` would do it.
  - Add `status == 'pending'` to `create_upload_url` and `complete_multipart_upload`.
  - Make `complete_transfer` refuse any status other than `pending`.
- **Vault namespace:** add one `file_id` validator (reject empty and `.`/`..` segments, a leading `/`, `\` and NUL) at the `Service__Vault__Pointer` entry points and in `path__vault_payload`. Mirror `Safe_Str__Vault__Append__File_Id`.
- **Caches:** move both services onto one manifest cache with a short TTL, and re-read storage on any key mismatch and before destroy-sensitive operations. Have `delete_vault` invalidate the append service as well.
- **Token check:**
  - Consolidate the four copies into `Service__Access_Token`.
  - Validate the token against `^[A-Za-z0-9_-]{1,64}$` and URL-quote it in `token_lookup`/`token_use`.
  - Require the lookup response's `token_name` to equal the token presented.
- **Public preview:** allowlist `image/png|jpeg|webp` and add `X-Content-Type-Options: nosniff`. Cache or rate-limit PBKDF2, and skip it when no preview exists.
- **Early access:** escape the email body with `html.escape`, bound the field lengths, and add a rate limit or dedupe.
- **Cold start:** pass `ExpectedBucketOwner` and pin the built zip's SHA-256 in deployed code, checked before extraction.

## 6. Hardening notes (not findings)

- **Token check and auth:**
  - The check fails open when there is no admin URL and the env token is empty. Require an explicit `SEND__OPEN_INSTANCE=true`.
  - The token is accepted via `?access_token=`, which puts it in logs.
  - Token comparisons use `!=` instead of `hmac.compare_digest`.
  - The 60 s positive cache keeps revoked tokens alive.
  - The anonymous check-token route is an oracle with no rate limit.
  - `token_use` runs after completion, its result is ignored, and it is non-atomic.
- **Vault lifecycle:**
  - `delete_vault` deletes the manifest before writing the tombstone; write the tombstone first.
  - Destroying a never-claimed ID writes a permanent tombstone (squatting, if the ID is known).
  - First-write-wins has no conditional put across processes.
  - Public-vault destroy also deletes the private zip cache for the same ID.
  - Presigned initiate on an unclaimed vault never claims it.
  - `read-url` still signs URLs for destroyed vaults.
- **Zip export:**
  - The cache is keyed on `file_id:size`, so same-size changes return a stale zip.
  - Entry names are raw `file_id`s, a zip-slip risk for clients that extract.
  - The build is unbounded in memory.
- **Presigned and multipart:**
  - No `ContentLength` binding, no `AbortIncompleteMultipartUpload` rule, and no per-token byte quota (from the rejected record).
  - 10,000-part initiates can exceed the Lambda response limit after the upload already exists.
  - `complete_*` accepts an unbounded parts list, and a malformed item returns a 500.
  - `cancel` returns a 500 for an unknown transfer.
- **Public preview:**
  - Anonymous views change transfer state.
  - `last_timings` is shared across requests, and the `public_id` is printed to logs.
  - The og:image URL is built from `Host`/`x-forwarded-proto`.
  - The thumbnail media-type regex allows CR/LF.
- **Info:** `/api/info/versions` discloses dependency versions, and the handler echoes init exceptions.
- **Cold start:**
  - An existing `/tmp` folder is trusted without a completion marker.
  - The zip key hashes package specs only, and the builder skips existing keys.
  - The builder targets cp313/x86_64, while the guidance says 3.12/arm64.
- **MCP:**
  - `/mcp` is unauthenticated; DNS-rebinding and Origin protection depend on fastapi-mcp defaults.
  - MCP calls likely record the transport IP in `ip_hash`.

**Positive patterns:**
- Append-lane identifiers are strictly typed and have traversal tests.
- The vault-ID regex blocks shard and ID collisions.
- `list` filters results back to the vault prefix.
- OG HTML is escaped.
- MCP forwards only the caller's own headers (the write key is not forwarded), so MCP grants no extra authority.
- CPython's `extractall` strips `..` from zip member paths.

## 7. Coverage

| Status | Count | Units |
|---|---|---|
| candidate | 8 | A1 token check, A2 vault ownership, A3 vault namespace, A4 transfers, A5 presigned/append, A6 anonymous routes, A7 MCP/cold start, A8 multipart (wave 2) |
| deferred | 1 | **A9 public-bucket lane**: `X-Vault-Public` gives the same `vault_id` a separate first-write claim, and `public-vault.json` publishes the caller's read key with no owner binding or lifecycle handling. Reason: `budget_cannot_reserve_critics_and_validation` |

How coverage evolved:
- The wave-1 critic added A8.
- The wave-2 critic found A9, which the remaining budget could not fund.
- **No final-clean critic ran, so no clean-coverage claim is made.**

Start the next run with A9, then re-run every lead above with the pinned dependencies available offline.
