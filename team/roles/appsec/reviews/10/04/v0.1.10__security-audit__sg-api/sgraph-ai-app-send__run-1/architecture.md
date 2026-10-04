# Architecture — SG/API (SGraph Send User Lambda) @ 5d50ae83, scoped to the extraction set

**Product & principals.** FastAPI service (`sgraph_ai_app_send/lambda__user/fast_api/Fast_API__SGraph__App__Send__User.py`) for zero-knowledge encrypted transfers and the sgit encrypted vault blob store. Clients encrypt; the server should hold ciphertext only. Principals: anonymous internet caller; global access-token holder (`x-sgraph-access-token`, one token not bound to any resource); vault writer (`x-sgraph-vault-write-key`, unsalted SHA-256 stored in the vault's `manifest.json`); append-token holder; enum-key holder; transfer deleter (`x-sgraph-transfer-delete-auth`); MCP clients; the Admin Lambda (token lookup/use, called with an admin API key from env). Protected: other users' vault objects and refs (integrity/availability — ciphertext confidentiality comes from client keys), transfer payload lifecycle (expiry/max_downloads), the access-token gate, the admin API key, operator spend, the Lambda's code integrity.

**Comparable baseline.** Git smart-HTTP / object stores with presigned S3 multipart flows; MCP streamable-HTTP server. Use to calibrate only.

**Stack & limits.** Python 3.12, osbot-fast-api-serverless (`Serverless__Fast_API`), Mangum on Lambda (Function URL AuthType NONE, `Deploy__Service.py:83-112`), Memory-FS storage selected in `storage/Send__Config.py:37-77` (S3 / disk / memory), optional public bucket. Runtime deps not installed locally → source-only review; library semantics (Safe_Str__Id, Safe_Str__File__Path, Memory-FS path joins, fastapi-mcp tool exposure) are unobservable → needs_validation when decisive.

**Entry surfaces & key paths.**
- `/api/transfers/*` (`Routes__Transfers.py`, `service/Transfer__Service.py`), `/api/presigned/*` (`Routes__Presigned.py`, `service/Service__Presigned_Urls.py`).
- `/api/vault/{write,read,read-base64,delete,batch,list,health,zip,destroy,public-info}` (`Routes__Vault__Pointer.py`, `service/Service__Vault__Pointer.py`, `service/Service__Vault__Zip.py`); keys `{root}/vault/{vid[:2]}/{vid}/{file_id}/payload` (`storage/Storage__Paths.py:33`), `file_id` unvalidated `{file_id:path}`.
- `/api/vault/presigned/*` (`Routes__Vault__Presigned.py`, `service/Service__Vault__Presigned.py`), `/api/vault/append/*` (`Routes__Vault__Append.py`, `service/Service__Vault__Append.py`).
- `/api/public-preview/*` (`Routes__Public_Preview.py`, `service/Public_Preview__Service.py`), `/api/early-access/signup`, `/api/info/*`, `/mcp` (`utils/MCP__Setup.py`).
- Cold start: `lambda_function/lambda_handler__user.py` → `_for_osbot_aws/Lambda__Dependencies__Loader.py` (S3 zip → extractall → sys.path[0]).

**Trust boundaries & strongest visible control.**
1. Access-token gate — four separate copies (`Service__Access_Token.py:30-73`, `Routes__Transfers.py:37-71`, `Routes__Presigned.py:163-187`, `Routes__Vault__Presigned.py:35-59`); fail-open when no admin client and empty env token; raw token into admin URL path (`Admin__Service__Client.py:23`).
2. Vault ownership — manifest write-key hash, first-write-wins, per-instance manifest cache, non-atomic CAS (`Service__Vault__Pointer.py:47-136`); public bucket has separate manifests.
3. Vault namespace — `vault_id` regex; `file_id`/`prefix` unvalidated into storage keys and zip entry names.
4. Transfer lifecycle — status/expiry/max_downloads in `Transfer__Service.get_download_payload`; parallel presigned download/upload paths with weaker checks.
5. Vault presigned / append — unclaimed-vault acceptance, unauthenticated read-url, configure-supplied anchors.
6. Anonymous preview/early-access — PBKDF2 600k per request, content-type from decrypted data, unescaped HTML email.
7. MCP — unauthenticated mount exposing tagged routes as tools, forwarding `authorization`/`x-sgraph-access-token`.
8. Code integrity — cold-start dependency zip from S3 without content integrity.

**Prior coverage.** No prior ledger for this repo/scope.

**Companion selection.** WEB-PROTOCOL-AND-AUTH (API-key scope, credential exposure — boundary 1); DATA-ISOLATION-AND-LIFECYCLE (vault namespace, signed-reference overreach, deletion/tombstone — 2,3,5); RESOURCE-EXHAUSTION-AND-AVAILABILITY (PBKDF2, zip build, presigned part signing — 6, 3); AI-AND-LLM MCP blocks (7); SUPPLY-CHAIN-AND-RELEASE mutable build inputs (8). Excluded: CLIENT-SIDE (vault web UI out of scope, except server-served active content handled in unit A6), MEMORY-SAFETY, DESKTOP-MOBILE, PROTOCOLS-RPC (no broker/RPC).
