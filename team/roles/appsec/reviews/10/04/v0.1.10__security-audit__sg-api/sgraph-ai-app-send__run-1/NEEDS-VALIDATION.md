# Needs validation — SG/API extraction set (SGraph-AI__App__Send @ 5d50ae83)

These are source-grounded leads with an exact unresolved fact. They carry **no severity** and are not confirmed vulnerabilities. Resolve them with the bounded local plan (which needs the pinned dependencies available offline) or the owner-observed check. Never send audit traffic to a deployment.

## Public preview og-image serves an author-chosen Content-Type (e.g. text/html) from the API origin

Fingerprint `Public_Preview__Service.thumbnail_bytes:data-url-media-type-reflected`

GET /api/public-preview/og-image/{public_id} is anonymous. It loads the transfer whose id is SHA-256('pvp-transfer-v1:'+public_id)[:12], decrypts it with a key publicly derivable from public_id (PBKDF2), takes the MIME type from the decrypted thumbnail's data: URL via ^data:([^;]+);base64,(.*)$, and returns it unchanged as Response(media_type=media) with Cache-Control: public, max-age=300. Anyone holding the global access token can create a transfer at the derived 12-hex id, upload a preview whose thumbnail is data:text/html;base64,<html+script>, and have the API origin serve that HTML to any anonymous visitor. The out-of-scope UI client (sgraph_ai_app_send__ui__open .../api-client.js lines 5 and 52) indicates production UI calls same-origin /api/* and keeps the access token in localStorage, so if the API shares that origin, served script could read the token. The [^;]+ group also matches CR/LF; header-splitting depends on Starlette/Mangum encoding (unverified). The source trace is confirmed; browser-visible impact depends on library and deployment facts.

**Claimed root cause.** Public_Preview__Service.thumbnail_bytes returns the author-supplied data: URL media type (lines 163/167) and Routes__Public_Preview.og_image__public_id uses it as the response Content-Type (line 54) with no image allowlist and no nosniff/attachment/CSP headers.

### Trace

1. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Public_Preview.py:49` (entrypoint, Routes__Public_Preview.og_image__public_id): Anonymous GET; no token check; API-key middleware disabled (Fast_API__SGraph__App__Send__User.py:59).
2. `sgraph_ai_app_send/lambda__user/service/Public_Preview__Service.py:59` (propagation, Public_Preview__Service.fetch_preview): Loads the payload of the transfer derived from public_id.
3. `sgraph_ai_app_send/lambda__user/service/Public_Preview__Service.py:64` (propagation, Public_Preview__Service.fetch_preview): Decrypts with PBKDF2(public_id); checks only schema and non-empty title.
4. `sgraph_ai_app_send/lambda__user/service/Public_Preview__Service.py:163` (propagation, Public_Preview__Service.thumbnail_bytes): Regex captures any media type; line 167 returns it with decoded bytes.
5. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Public_Preview.py:54` (sink, Routes__Public_Preview.og_image__public_id): Response(content=raw, media_type=media, public cache) serves author bytes with author Content-Type.

### Evidence

- `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:44`: TRANSFER_ID_PATTERN accepts client-chosen 12-hex ids.
- `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Transfers.py:91`: Transfer create gated only by the global access token.
- `sgraph_ai_app_send/lambda__user/fast_api/Fast_API__SGraph__App__Send__User.py:150`: Public preview routes mounted on the same app as all /api/* routes.
- `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:146`: get_download_payload applies no content-type constraint.

### Blockers

- Starlette/FastAPI Response media_type handling for arbitrary or CR/LF-containing types (deps not installed).
- Whether /api/* is served from the same origin as the UI that stores the token in localStorage (CloudFront behaviours).
- Edge-added headers (nosniff, CSP, Content-Disposition) that could neutralise rendering.
- How widely the global access token is distributed.

### Resolution plan

- **Local (bounded):** In an isolated venv with only pinned starlette/fastapi (no target code), return Response(content=b'<script>1</script>', media_type='text/html') and a CR/LF variant via TestClient and record headers; separately apply the regex at Public_Preview__Service.py:163 to 'data:text/html;base64,PHNjcmlwdD4=' and confirm group(1)=='text/html'.
- **Owner-observed:** Owner observes (no audit traffic): CloudFront behaviours for /api/public-preview/* vs the UI origin; response-header policies on og-image; number of holders of the global access token.

## Anonymous /api/public-preview/info runs 600k-iteration PBKDF2 unconditionally (twice on a hit)

Fingerprint `Routes__Public_Preview.info__public_id:unconditional-pbkdf2-600k`

GET /api/public-preview/info/{public_id} needs no authentication. Every call runs read_key_base64url(public_id) (Routes__Public_Preview.py:62), i.e. PBKDF2-HMAC-SHA256 with 600000 iterations (Public_Preview__Service.py:25, :40), even when no preview exists; on a hit fetch_preview runs a second derivation (:63) and get_download_payload also rewrites transfer metadata (Transfer__Service.py:160-165). The caller pays one small GET; the server pays ~0.6-1.2M HMAC iterations of CPU inside the same User Lambda that serves every /api/vault, /api/transfers and /mcp route. No cache, rate limit or concurrency guard is visible. Whether this produces shared impact (concurrency exhaustion or operator spend) depends on deployed WAF, CloudFront caching and reserved concurrency.

**Claimed root cause.** info__public_id calls the 600k-iteration derivation for every anonymous request regardless of existence, and repeats it on a hit, with no source-visible caching or rate limiting.

### Trace

1. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Public_Preview.py:56` (entrypoint, Routes__Public_Preview.info__public_id): Anonymous GET with any public_id.
2. `sgraph_ai_app_send/lambda__user/service/Public_Preview__Service.py:63` (propagation, Public_Preview__Service.fetch_preview): First derivation on a hit.
3. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Public_Preview.py:62` (propagation, Routes__Public_Preview.info__public_id): read_key_base64url evaluated on every request.
4. `sgraph_ai_app_send/lambda__user/service/Public_Preview__Service.py:40` (sink, Public_Preview__Service.derive_read_key_bytes): hashlib.pbkdf2_hmac with 600000 iterations, CPU-bound in the shared Lambda.

### Evidence

- `sgraph_ai_app_send/lambda__user/service/Public_Preview__Service.py:25`: PREVIEW_ITERATIONS = 600000.
- `sgraph_ai_app_send/lambda__user/fast_api/Fast_API__SGraph__App__Send__User.py:150`: Same app and concurrency pool as vault/transfer/MCP routes.
- `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:160`: On a hit each anonymous fetch rewrites transfer metadata.
- `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Public_Preview.py:66`: No rate-limit or cache decorator on the preview routes.

### Blockers

- Deployed WAF rate rules or CloudFront caching on /api/public-preview/info/*.
- Lambda reserved/account concurrency and whether throttling affects other /api routes.
- Measured per-invocation PBKDF2 duration at the deployed memory size.

### Resolution plan

- **Local (bounded):** Stdlib-only fixture under unshare -rn env -i timeout prlimit: time hashlib.pbkdf2_hmac('sha256', b'abc', b'salt', 600000, dklen=32) over 5 runs to record per-call CPU seconds (no target code).
- **Owner-observed:** Owner observes: User Lambda reserved concurrency and memory; WAF/CloudFront rules on /api/public-preview/*; CloudWatch Duration and Throttles for public-preview invocations.

## Unescaped anonymous signup name/email/Accept-Language are injected into the HTML operator email

Fingerprint `Service__Early_Access.build_email_body:unescaped-html-and-locale`

POST /api/early-access/signup takes a caller-supplied name (plain str, no length or character limit) and an email that only has to match ^[^@\s]+@[^@\s]+\.[^@\s]+$ (so <, >, " and ' pass); the locale falls back to the raw first Accept-Language token. All three are placed into an HTML body (<br>, <b> markup) and the subject via f-strings without escaping, then posted to the n8n webhook which sends from the project's own mailbox to fixed operator addresses. A caller who knows only the public route can inject arbitrary HTML (links, forms, spoofed rows) into an email arriving from a trusted internal sender. Whether it renders depends on the n8n workflow and WorkMail send step, not in this repo. The module imports osbot_utils Type_Safe (not installed), so no stdlib fixture of build_email_body was possible.

**Claimed root cause.** Service__Early_Access.build_email_body builds an HTML body and subject by f-string interpolation of untrusted name, email and locale without html.escape; the input checks do not exclude HTML metacharacters.

### Trace

1. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Early_Access.py:20` (entrypoint, Routes__Early_Access.signup): Anonymous POST; registered at Fast_API__SGraph__App__Send__User.py:137.
2. `sgraph_ai_app_send/lambda__user/service/Service__Early_Access.py:26` (propagation, Service__Early_Access._is_valid_email): Permissive email regex; validate_signup only requires a non-blank name.
3. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Early_Access.py:55` (propagation, Routes__Early_Access._detect_locale): Locale from the raw first Accept-Language token.
4. `sgraph_ai_app_send/lambda__user/service/Service__Early_Access.py:31` (propagation, Service__Early_Access.build_email_body): Unescaped interpolation into the HTML body (31-35) and subject (30).
5. `sgraph_ai_app_send/lambda__user/service/Service__Early_Access.py:69` (sink, Service__Early_Access._call_webhook): Payload POSTed to the n8n webhook which sends the email.

### Evidence

- `sgraph_ai_app_send/lambda__user/schemas/Schema__Early_Access.py:10`: name is a plain str with no bound or restriction.
- `sgraph_ai_app_send/lambda__user/service/Service__Early_Access.py:44`: Recipients are fixed operator addresses.
- `sgraph_ai_app_send/lambda__user/service/Service__Early_Access.py:8`: Module imports osbot_utils Type_Safe (not installed).
- `sgraph_ai_app_send/lambda__user/fast_api/Fast_API__SGraph__App__Send__User.py:59`: enable_api_key = False: global API-key middleware disabled; the early-access route has no per-route token check.

### Blockers

- Whether the n8n send_email step and WorkMail send the body as text/html or escape it (hosted platform, not in repo).

### Resolution plan

- **Local (bounded):** Copy the body of build_email_body (Service__Early_Access.py:29-38) into a stdlib-only script (no target imports) under unshare -rn env -i timeout prlimit and call it with name='<a href="https://example.invalid">x</a>', email='a"<b>@x.yz', locale='<i>q</i>'; confirm markup passes through. Never call the webhook.
- **Owner-observed:** Owner inspects the n8n workflow behind N8N_WEBHOOK_URL for the send_email body type (Html vs Text) and escaping, and a past signup notification's Content-Type. Do not send test signups.

## Anonymous early-access signup triggers two outbound n8n email sends per request with no rate or size bound

Fingerprint `Service__Early_Access.send_notification:unthrottled-anonymous-webhook-fanout`

Each valid anonymous POST /api/early-access/signup calls send_notification, which loops over two fixed recipients and makes a synchronous urllib POST to the n8n webhook per recipient (10 s timeout each), holding the invocation for up to ~20 s while n8n is slow. No rate limit, CAPTCHA, deduplication or name-size bound is visible, and the route is also an MCP-exposed tag. Repetition yields two n8n executions and two operator emails per request: operator spend and inbox flooding. Recipients are fixed, so this is operator-owned cost, not other tenants' data. Impact depends on deployed upstream controls (concurrency, WAF, n8n quota, mail limits). The issue applies only when N8N_WEBHOOK_URL is configured.

**Claimed root cause.** send_notification does two synchronous outbound webhook calls per anonymous request with no source-visible rate limit, deduplication or input bound.

### Trace

1. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Early_Access.py:20` (entrypoint, Routes__Early_Access.signup): Anonymous POST; calls send_notification at line 36.
2. `sgraph_ai_app_send/lambda__user/service/Service__Early_Access.py:44` (propagation, Service__Early_Access.send_notification): Loops over two fixed recipients.
3. `sgraph_ai_app_send/lambda__user/service/Service__Early_Access.py:74` (sink, Service__Early_Access._call_webhook): Synchronous urlopen POST with timeout=10; each triggers an n8n execution and an email.

### Evidence

- `sgraph_ai_app_send/lambda__user/fast_api/Fast_API__SGraph__App__Send__User.py:158`: 'api/early-access' is an MCP-exposed tag.
- `sgraph_ai_app_send/lambda__user/fast_api/Fast_API__SGraph__App__Send__User.py:87`: Service built from N8N_WEBHOOK_URL/SECRET; empty URL means no outbound call.
- `sgraph_ai_app_send/lambda__user/lambda_function/deploy/Deploy__Service.py:87`: Function URL AuthType NONE; no reserved concurrency or WAF in repo.
- `sgraph_ai_app_send/lambda__user/schemas/Schema__Early_Access.py:10`: name is unbounded.
- `sgraph_ai_app_send/lambda__user/fast_api/Fast_API__SGraph__App__Send__User.py:59`: enable_api_key = False: global API-key middleware disabled; the early-access route has no per-route token check.

### Blockers

- Deployed upstream controls (reserved concurrency, WAF rate rules, account throttles).
- n8n plan execution quota/overage behaviour and WorkMail/SES sending limits.

### Resolution plan

- **Owner-observed:** Owner checks without audit traffic: User Lambda reserved concurrency and any WAF/CloudFront rate rule; n8n plan quota and whether other workflows stop when exceeded; WorkMail/SES quotas for the sending accounts.

## User Lambda imports dependency code from an S3 object found by a predictable name, with no bucket-owner or content-digest check

Fingerprint `sgraph_ai_app_send/_for_osbot_aws/Lambda__Dependencies__Loader.py:load:unverified-s3-dependency-zip`

On cold start (AWS_REGION set), lambda_handler__user.py calls load_combined_dependency('sgraph-send-user', ...). The loader derives bucket '{account_id}--osbot-lambdas--{region}' and key 'lambdas-dependencies-combined/sgraph-send-user-{sha256(sorted package list)[:12]}.zip' (a hash of requirement strings, not zip bytes), calls s3.get_object with no ExpectedBucketOwner and no digest/signature check, runs extractall into /tmp, and inserts it at sys.path[0] before the app (and the admin-API-key-bearing environment) is imported. The builder skips upload when the key exists, so a planted object persists across redeploys. Source shows no lower-trust writer: request-driven storage uses separate buckets and the only writer is the credentialed deployer, so a same-account writer is normally as privileged as the deployer (hardening). The case source cannot settle is cross-account bucket pre-creation: the name contains only account id and region, so if the bucket does not exist in a deployed region another account could create it, and with no ExpectedBucketOwner the loader would fetch and run that account's code. CPython's extractall strips '..' and absolute members, so this is code shadowing via sys.path, not zip-slip.

**Claimed root cause.** Lambda__Dependencies__Loader.load trusts whatever object sits at a name-derived bucket/key: the bucket is predictable and not owner-pinned, the key is derived from the package list rather than an artifact digest, and no integrity check runs before extracted code is placed first on sys.path; Builder.upload's skip-if-exists never re-checks an existing object.

### Trace

1. `sgraph_ai_app_send/lambda__user/lambda_function/lambda_handler__user.py:12` (entrypoint, module import (cold start, guarded by AWS_REGION at line 6)): Calls load_combined_dependency before importing the FastAPI app.
2. `sgraph_ai_app_send/_for_osbot_aws/Lambda__Dependencies__Loader.py:27` (propagation, _deps_hash): Object identity is sha256 of package-name strings, truncated to 12 hex.
3. `sgraph_ai_app_send/_for_osbot_aws/Lambda__Dependencies__Loader.py:84` (propagation, Lambda__Dependencies__Loader.load): Bucket name from STS account id and region only.
4. `sgraph_ai_app_send/_for_osbot_aws/Lambda__Dependencies__Loader.py:89` (propagation, Lambda__Dependencies__Loader.load): get_object without ExpectedBucketOwner; bytes not checked against any digest.
5. `sgraph_ai_app_send/_for_osbot_aws/Lambda__Dependencies__Loader.py:96` (propagation, Lambda__Dependencies__Loader.load): extractall into /tmp (CPython strips '..').
6. `sgraph_ai_app_send/_for_osbot_aws/Lambda__Dependencies__Loader.py:99` (sink, Lambda__Dependencies__Loader.load): sys.path.insert(0, temp_folder): subsequent imports run code from the object.

### Evidence

- `sgraph_ai_app_send/lambda__user/lambda_function/lambda_handler__user.py:6`: Loader runs on every cold start without a /tmp cache.
- `sgraph_ai_app_send/_for_osbot_aws/Lambda__Dependencies__Loader.py:60`: Fixed, predictable key prefix.
- `sgraph_ai_app_send/lambda__user/user__config.py:6`: Package list feeding the key hash is public source.
- `sgraph_ai_app_send/_for_osbot_aws/Lambda__Dependencies__Builder.py:124`: upload() skips if the key exists; existing objects never re-verified.
- `sgraph_ai_app_send/_for_osbot_aws/Lambda__Dependencies__Builder.py:135`: put_object without ExpectedBucketOwner; no digest recorded.
- `sgraph_ai_app_send/lambda__user/lambda_function/deploy/Deploy__Service.py:35`: Admin API key in the Lambda environment, reachable by loaded code.
- `sgraph_ai_app_send/lambda__user/storage/Send__Config.py:18`: Request-driven storage uses separate buckets; no API path writes the osbot-lambdas bucket.

### Blockers

- Whether '{account_id}--osbot-lambdas--{region}' exists and is owned by the deploying account in every deployed region (cross-account pre-creation).
- Bucket policy/ACL/Object Ownership/BPA and the principals with s3:PutObject on lambdas-dependencies-combined/* — whether any is less trusted than the deployer.
- osbot-aws deploy behaviour (bucket creation/ownership assertion) is not installed.

### Resolution plan

- **Local (bounded):** Stdlib-only fixture (no target imports) under unshare -rn env -i timeout prlimit: recompute the key from the public package list; build a scratch zip with a marker 'fastapi/__init__.py', extract, insert at sys.path[0], import, observe the marker. Shows the shadowing mechanism only.
- **Owner-observed:** Owner, per deployed region, non-destructively: head-bucket --expected-bucket-owner <account_id>; get-bucket-policy/acl/ownership-controls/public-access-block; enumerate principals with s3:PutObject on the key (Access Analyzer or policy simulation); compare the object's ETag/LastModified with the deploy run. Otherwise treat as hardening: add ExpectedBucketOwner and pin the built zip's SHA-256 in deployed code.

## Raw x-sgraph-access-token header is interpolated into the admin token-lookup URL path; a caller may steer the gate to another admin GET returning status 'active'

Fingerprint `sgraph_ai_app_send/lambda__user/service/Admin__Service__Client.py:token_lookup:unsanitized-token-in-admin-path`

Four user-Lambda access-token gates (Service__Access_Token via Routes__Vault__Pointer and Routes__Vault__Append, plus the inline copies in Routes__Presigned and Routes__Vault__Presigned) pass the raw x-sgraph-access-token header value to Admin__Service__Client.token_lookup, which builds f'/tokens/lookup/{token_name}' with no encoding or validation and sends it with the admin API key. The gate accepts any JSON response with status == 'active', and Service__Access_Token caches that positive result for the TTL. If the transport or the admin front door resolves dot-segments, a header such as '../../rooms/lookup/<room_id>' could reach a different admin GET handler (e.g. lambda__admin Routes__Data_Room.lookup__room_id, whose records are stored with status='active'), so the gate would pass for a caller holding no valid access token. The sibling gate in Routes__Transfers sanitises with Safe_Str__Id first; the other copies do not. Whether the bypass works depends on library and deployment path handling that is not installed or observable here.

**Claimed root cause.** Admin__Service__Client.token_lookup (Admin__Service__Client.py:24) inserts a caller-controlled header value into the admin request path without percent-encoding or charset restriction; three of four gate copies (Service__Access_Token.py:40, Routes__Presigned.py:36, Routes__Vault__Presigned.py:42) do not sanitise it first; acceptance depends only on the response's status field (Service__Access_Token.py:44), not on the response being the token record that was requested.

### Trace

1. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Vault__Pointer.py:65` (entrypoint, Routes__Vault__Pointer.check_access_token): Reads the raw x-sgraph-access-token header from an unauthenticated request (vault write/delete/batch). Equivalent raw reads at Routes__Vault__Append.py:45, Routes__Presigned.py:30, Routes__Vault__Presigned.py:36.
2. `sgraph_ai_app_send/lambda__user/service/Service__Access_Token.py:40` (propagation, Service__Access_Token.check): Passes the token unmodified to admin_service_client.token_lookup in REMOTE mode.
3. `sgraph_ai_app_send/lambda__user/service/Admin__Service__Client.py:24` (propagation, Admin__Service__Client.token_lookup): Builds f'/tokens/lookup/{token_name}' and executes GET via Fast_API__Client__Requests; no encoding or validation.
4. `sgraph_ai_app_send/lambda__user/service/Admin__Service__Client__Setup.py:38` (propagation, setup_admin_service_client__remote): REMOTE client sends to the admin base_url with the admin API key, so any admin GET the path resolves to is authorised.
5. `sgraph_ai_app_send/lambda__user/service/Service__Access_Token.py:44` (sink, Service__Access_Token.check): Any JSON response with status == 'active' passes; line 47 caches it as a positive for ttl_seconds.

### Evidence

- `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Transfers.py:42`: Sibling gate sanitises with Safe_Str__Id before token_lookup (the intended invariant).
- `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Presigned.py:36`: Inline gate copy: raw header to token_lookup; accepts status == 'active' (39-40).
- `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Vault__Presigned.py:42`: Inline gate copy: raw header to token_lookup; accepts status == 'active' (46).
- `sgraph_ai_app_send/lambda__admin/fast_api/routes/Routes__Data_Room.py:52`: Example alternate admin GET /rooms/lookup/{room_id} returns the stored room dict.
- `sgraph_ai_app_send/lambda__admin/service/Service__Data_Room.py:51`: Room records are stored with status='active'.
- `sgraph_ai_app_send/lambda__admin/fast_api/routes/Routes__Tokens.py:49`: Intended target is a single-segment parameter; a slash-containing value cannot match it, so the bypass needs path normalisation before routing (otherwise 404 -> 401).

### Blockers

- osbot-fast-api Fast_API__Client__Requests REMOTE mode: how it joins base_url and path and whether its HTTP stack removes '../' dot-segments or percent-decodes before sending (not installed).
- How the admin Lambda front door (Function URL / Mangum / Starlette routing) handles dot-segments or encoded slashes (deployment-dependent).
- Whether a caller without a token can learn the identifier of an admin object whose lookup returns status 'active' (data state and id exposure).

### Resolution plan

- **Local (bounded):** In an offline sandbox with pinned deps pre-installed (no network, empty env, read-only tree, low limits), start the admin FastAPI app on loopback with a dummy API key, seed one dummy room, register Admin__Service__Client in REMOTE mode against it, call Service__Access_Token(admin_service_client=client).check('../../rooms/lookup/<dummy_room_id>') and the %2F-encoded variant; record the path the admin server logs and whether check returns or raises 401.
- **Owner-observed:** Owner-observed from config and package metadata only: whether the admin front door normalises dot-segments or decodes %2F before routing, and which HTTP library/version Fast_API__Client__Requests uses in the deployed user Lambda.

## Unauthenticated presigned download-url bypasses transfer expiry and max_downloads (and never triggers auto_delete)

Fingerprint `sgraph_ai_app_send/lambda__user/service/Service__Presigned_Urls.py:create_download_url:lifecycle-predicates-omitted`

GET /api/presigned/download-url/{transfer_id} has no access-token check. create_download_url gates only on status == 'completed', increments download_count without comparing to max_downloads, never calls _is_expired, never applies the auto_delete/exhaust transition, and returns a 1-hour presigned S3 GET for the payload. The direct path (get_download_payload) enforces expiry (410), max_downloads (410) and auto_delete exhaustion. Anyone who knows a transfer_id (a recipient of a one-time/expiring link, or anyone it was forwarded to) can keep fetching the ciphertext after expiry or after the limit, for every expired transfer and every max_downloads transfer with auto_delete=False (they never leave 'completed'); auto_delete=True transfers are only protected once exhausted through the direct path. The data is ciphertext, so the broken boundary is the server-enforced lifecycle/retention guarantee, not plaintext confidentiality. Large files (>5 MB) are directed to this path by design.

**Claimed root cause.** Two code paths serve the same payload; only Transfer__Service.get_download_payload applies the lifecycle predicates. Service__Presigned_Urls.create_download_url re-implements the bookkeeping but checks only status == 'completed', and its route has no per-route token check (global API-key middleware is disabled).

### Trace

1. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Presigned.py:142` (entrypoint, Routes__Presigned.download_url__transfer_id): No check_access_token (unlike upload_url at line 130); passes transfer_id to the service (145).
2. `sgraph_ai_app_send/lambda__user/service/Service__Presigned_Urls.py:198` (propagation, Service__Presigned_Urls.create_download_url): Only gate is status != 'completed'; no _is_expired or max_downloads check.
3. `sgraph_ai_app_send/lambda__user/service/Service__Presigned_Urls.py:202` (propagation, Service__Presigned_Urls.create_download_url): Increments and saves download_count (209) without comparison; no exhaust transition.
4. `sgraph_ai_app_send/lambda__user/service/Service__Presigned_Urls.py:213` (sink, Service__Presigned_Urls.create_download_url): Presigned get_object URL valid 3600 s, independent of expires_at.

### Evidence

- `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:153`: Direct path: expired returns 410.
- `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:157`: Direct path: download_count >= max_downloads returns 410.
- `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:169`: Direct path: auto_delete deletes payload and sets 'exhausted'.
- `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Transfers.py:179`: Files over 5 MB are refused on the direct path and pointed to the presigned path.
- `sgraph_ai_app_send/lambda__user/fast_api/Fast_API__SGraph__App__Send__User.py:59`: enable_api_key = False: per-route checks are the only gate.
- `sgraph_ai_app_send/lambda__user/fast_api/Fast_API__SGraph__App__Send__User.py:75`: Presigned service gets a real S3 client only with Storage_FS__S3.
- `sgraph_ai_app_send/lambda__user/schemas/Schema__Transfer.py:20`: max_downloads, auto_delete, expires_at are client-set lifecycle controls.

### Blockers

- Whether the deployed User Lambda runs in S3 storage mode (otherwise the path returns presigned_not_available).
- osbot_aws S3.create_pre_signed_url semantics (not installed).
- Safe_Str__Id preserving a 12-hex transfer_id unchanged (not installed).
- Whether an out-of-repo S3 lifecycle rule deletes expired payloads (narrows the expiry bypass only).

### Resolution plan

- **Local (bounded):** With pinned deps installed and no network: Transfer__Service(Storage_FS__Memory()); create max_downloads=1, auto_delete=False, expires_at=1; upload 16 dummy bytes; complete; confirm get_download_payload returns 'expired'. Build Service__Presigned_Urls with storage_mode S3 and a local stand-in s3 whose create_pre_signed_url returns 'presigned:'+object_name; call create_download_url twice and observe two URLs and download_count 2.
- **Owner-observed:** Owner-observed: confirm production storage mode is S3 and is_s3_mode() is True; whether any S3 lifecycle rule removes expired payloads; deployed osbot-aws/osbot-utils versions.

## Presigned upload-url lacks a pending-state check: completed transfers can be overwritten and deleted or exhausted transfers resurrected

Fingerprint `sgraph_ai_app_send/lambda__user/service/Service__Presigned_Urls.py:create_upload_url:missing-pending-state-check`

GET /api/presigned/upload-url/{transfer_id} requires only the global, non-resource-bound access token. create_upload_url checks only that the transfer exists, then returns a 1-hour presigned put_object URL for its payload key. The pending-only invariant enforced by upload_payload and by presigned multipart initiate is missing, and transfer metadata records no creator. Any access-token holder who knows another user's transfer_id can replace a completed transfer's ciphertext: corruption without the key (availability) and, for a recipient holding the key, substitution of content that decrypts validly for other recipients (integrity). complete_transfer has no status predicate either, so once a payload exists again POST /api/transfers/complete re-marks a 'deleted' tombstone or 'exhausted' transfer as 'completed', reversing the sender's delete or one-time burn (exhausted ones are then served by the presigned download path).

**Claimed root cause.** create_upload_url authorizes on existence plus a global token, omitting the status == 'pending' predicate applied by upload_payload and initiate_multipart_upload; transfers have no owner binding; complete_transfer re-sets status to 'completed' from any prior state.

### Trace

1. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Presigned.py:127` (entrypoint, Routes__Presigned.upload_url__transfer_id): check_access_token (130) validates only the global token; open if none configured (50).
2. `sgraph_ai_app_send/lambda__user/service/Service__Presigned_Urls.py:232` (propagation, Service__Presigned_Urls.create_upload_url): Only gate is has_transfer; no status check unlike initiate (54-57).
3. `sgraph_ai_app_send/lambda__user/service/Service__Presigned_Urls.py:237` (propagation, Service__Presigned_Urls.create_upload_url): Presigned put_object URL (3600 s) on the transfer payload key.
4. `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:112` (sink, Transfer__Service.complete_transfer): With a payload present (110), status set to 'completed' unconditionally, resurrecting 'deleted' (193) and 'exhausted' transfers.

### Evidence

- `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:97`: Direct path rejects status != 'pending'.
- `sgraph_ai_app_send/lambda__user/service/Service__Presigned_Urls.py:56`: Presigned initiate returns transfer_not_pending.
- `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:74`: Meta has no creator/owner binding.
- `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:193`: Delete leaves a tombstone meant to be permanent.
- `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Transfers.py:134`: POST /api/transfers/complete calls complete_transfer with no state check.
- `sgraph_ai_app_send/lambda__user/storage/Storage_FS__S3.py:38`: In-repo s3_key is str(path) plus an optional prefix; Send__Config.py:76 constructs it with no prefix, so has_payload checks the same key the presigned PUT writes.

### Blockers

- Whether production runs in S3 storage mode with an S3 client wired.
- osbot_aws put_object presign semantics (unconditional overwrite).
- How access tokens are issued in production (shared vs per-user), which sets how lower-trust the writer is.
- Whether Safe_Str__File__Path (osbot-utils, not installed) leaves the payload path unchanged when Storage_FS__S3.file__exists coerces it.

### Resolution plan

- **Local (bounded):** With pinned deps and no network: Transfer__Service(Storage_FS__Memory()); create transfer A with delete_auth_hash; upload; complete; delete_transfer -> 'deleted'. Service__Presigned_Urls with S3 mode and a local stand-in s3: create_upload_url(A) returns a URL; write dummy bytes to payload_path(A); complete_transfer(A) -> status 'completed'.
- **Owner-observed:** Owner-observed: production storage mode S3; whether object lock/versioning or bucket policy prevents overwriting payload keys; how access tokens are issued.

## Vault append lane keeps authorizing writes/reads from a process-lifetime cache after vault destroy or anchor/enum-key revocation

Fingerprint `sgraph_ai_app_send/lambda__user/service/Service__Vault__Append.py:_load_manifest+_load_append_config:uninvalidated-auth-cache`

Service__Vault__Append keeps process-lifetime caches of the vault manifest and the append config (append_anchors, enum_key_hash) and returns cached entries without re-checking storage. Vault destroy runs on a separate Service__Vault__Pointer instance in the same process (append_service at Fast_API__SGraph__App__Send__User.py:92, vault_service at :95); delete_vault deletes manifest.json and bare/append/config.json but invalidates only the pointer's own cache. In one warm process that already served the vault's append routes: (a) an anonymous holder of a previously anchored append token can still POST /api/vault/append/write and recreate data under a destroyed vault; (b) an old enum-key holder can still list/fetch/mark-processed; (c) after purge plus re-claim with a new write key, the stale manifest makes the old owner's key pass configure/purge on the append lane and rejects the new owner's key there, so old token holders can inject entries into the new owner's vault and the new owner cannot replace anchors. Separately, configure on one process does not revoke anchors cached by other warm processes. (a)-(c) need only one warm process; the revocation gap needs several.

**Claimed root cause.** Service__Vault__Append._load_manifest (42-55) and _load_append_config (57-65) return cached entries for the process lifetime; nothing invalidates them when Service__Vault__Pointer.delete_vault removes the vault or another process rewrites config.json, so _check_append_token, _check_enum_key, _check_write_key and configure decide against stale data. Distinct from the pointer service's own manifest cache (different class, different fix).

### Trace

1. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Vault__Pointer.py:270` (entrypoint, Routes__Vault__Pointer.destroy__vault_id): Owner destroys the vault (optional purge), dispatched to vault_service.delete_vault (289).
2. `sgraph_ai_app_send/lambda__user/service/Service__Vault__Pointer.py:217` (propagation, Service__Vault__Pointer.delete_vault): Deletes all files under the vault prefix, including manifest.json and bare/append/config.json.
3. `sgraph_ai_app_send/lambda__user/service/Service__Vault__Pointer.py:221` (propagation, Service__Vault__Pointer.delete_vault): Invalidates only the pointer's own cache (221 pop, 229 tombstone).
4. `sgraph_ai_app_send/lambda__user/fast_api/Fast_API__SGraph__App__Send__User.py:92` (propagation, Fast_API__SGraph__App__Send__User.setup): append_service is a separate instance sharing only storage_fs.
5. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Vault__Append.py:48` (propagation, Routes__Vault__Append.write__vault_id): Anonymous append write; reaches append_service.append (62).
6. `sgraph_ai_app_send/lambda__user/service/Service__Vault__Append.py:43` (propagation, Service__Vault__Append._load_manifest): Cache hit returns the pre-destroy manifest; deleted-status gate (81) passes.
7. `sgraph_ai_app_send/lambda__user/service/Service__Vault__Append.py:58` (propagation, Service__Vault__Append._load_append_config): Cache hit returns pre-destroy anchors; anchor check (85) passes.
8. `sgraph_ai_app_send/lambda__user/service/Service__Vault__Append.py:139` (sink, Service__Vault__Append.append): file__save writes the payload under the destroyed or re-claimed vault's prefix.

### Evidence

- `sgraph_ai_app_send/lambda__user/service/Service__Vault__Append.py:30`: Cache attributes never cleared by any method.
- `sgraph_ai_app_send/lambda__user/service/Service__Vault__Append.py:104`: configure gates on the cached manifest's write_key_hash.
- `sgraph_ai_app_send/lambda__user/service/Service__Vault__Append.py:119`: configure updates only this process's config cache.
- `sgraph_ai_app_send/lambda__user/storage/Storage__Paths.py:52`: config.json and pending files live under the vault prefix.
- `tests/unit/lambda__user/fast_api/routes/test_Routes__Vault__Pointer.py:680`: purge then re-claim is a tested, intended flow.
- `tests/unit/lambda__user/service/test_Service__Vault__Append.py:602`: Deleted-vault test pops the cache by hand before asserting the gate fails.
- `tests/unit/lambda__user/fast_api/routes/test_Routes__Vault__Append.py:109`: Route tests pop the cache after seeding storage out-of-band.

### Blockers

- Type_Safe per-instance dict initialisation for the underscore cache attributes and memory-fs folder__files__all/file__exists/file__save semantics (not installed).
- The cross-process revocation variant needs several concurrent warm environments sharing one bucket (deployment).

### Resolution plan

- **Local (bounded):** With pinned deps and no network, in-memory app + TestClient: owner writes vault 'staleapp0001' with K1; configure anchors=[sha256('tok1')], enum_key_hash; append once with 'tok1'; destroy (purge false); append again with 'tok1' -> 200 if vulnerable, check pending file next to deleted.json. Re-claim variant: purge true, new owner writes with K2, configure with K2 -> 403 and with K1 -> 200 if vulnerable.
- **Owner-observed:** Owner-observed only: whether the User Lambda runs with more than one concurrent environment (decides the cross-process variant only).

## Vault manifest cache is never revalidated: after destroy or purge plus re-claim, the old write key keeps write/delete/batch/destroy on other warm instances

Fingerprint `sgraph_ai_app_send/lambda__user/service/Service__Vault__Pointer.py:_load_manifest:manifest-cache-never-revalidated`

Service__Vault__Pointer caches each vault's manifest (or tombstone) for the process lifetime and returns it without re-checking storage; delete_vault invalidates only the instance that served the destroy. There is one pointer instance per backend per process, so a single-process exploit is not possible. If another concurrent warm environment cached the manifest earlier: (a) after a non-purge destroy it still accepts the old write key for write, delete, write_if_match, batch and delete_vault, recreating payloads under a tombstoned vault; (b) after purge plus re-claim by a new owner, it still authorizes the previous owner's key, letting them overwrite or delete the new owner's ciphertext or destroy the vault, while the new owner's key is rejected there. The attacker must hold an access token and the old write key.

**Claimed root cause.** _load_manifest (50-63) treats the process cache as authoritative; _check_vault_write_key (65-71) authorizes write/delete/write_if_match/batch/delete_vault against it; delete_vault invalidates only locally (221/229) and nothing revalidates across processes.

### Trace

1. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Vault__Pointer.py:270` (entrypoint, Routes__Vault__Pointer.destroy__vault_id): Destroy served by environment A.
2. `sgraph_ai_app_send/lambda__user/service/Service__Vault__Pointer.py:221` (propagation, Service__Vault__Pointer.delete_vault): Only A's cache is updated.
3. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Vault__Pointer.py:74` (propagation, Routes__Vault__Pointer.write__vault_id__file_id): PUT with the old write key served by warm environment B.
4. `sgraph_ai_app_send/lambda__user/service/Service__Vault__Pointer.py:51` (propagation, Service__Vault__Pointer._load_manifest): Cache hit returns the pre-destroy/pre-reclaim manifest.
5. `sgraph_ai_app_send/lambda__user/service/Service__Vault__Pointer.py:71` (propagation, Service__Vault__Pointer._check_vault_write_key): Compares against the stale write_key_hash; deleted gate (69) never reached.
6. `sgraph_ai_app_send/lambda__user/service/Service__Vault__Pointer.py:91` (sink, Service__Vault__Pointer.write): file__save of attacker bytes (also delete 110, batch 181/195, delete_vault 217).

### Evidence

- `sgraph_ai_app_send/lambda__user/service/Service__Vault__Pointer.py:26`: Lambda-lifetime cache with no TTL.
- `sgraph_ai_app_send/lambda__user/service/Service__Vault__Pointer.py:62`: Manifest cached on first load, never revalidated.
- `sgraph_ai_app_send/lambda__user/fast_api/Fast_API__SGraph__App__Send__User.py:95`: One private-bucket vault_service per process.
- `tests/unit/lambda__user/service/test_Service__Vault__Pointer.py:547`: Tests never model a second warm instance.
- `tests/unit/lambda__user/fast_api/routes/test_Routes__Vault__Pointer.py:680`: purge then re-claim is an intended flow.

### Blockers

- Whether the User Lambda runs several concurrent warm environments against the same bucket (no reserved concurrency in repo).
- Type_Safe/memory-fs semantics for a two-instance reproduction (not installed).

### Resolution plan

- **Local (bounded):** With pinned deps and no network: one Storage_FS__Memory, two Service__Vault__Pointer instances A and B; write via A with K1; B.write with K1 (warms B); A.delete_vault(K1); B.write(...,K1) non-None if vulnerable. Re-claim: A.delete_vault(purge=True), A.write with K2, B.write with K1 non-None and with K2 None if vulnerable.
- **Owner-observed:** Owner-observed only: User Lambda concurrency settings and whether ConcurrentExecutions > 1 for /api/vault traffic.

## Concurrent downloads can exceed max_downloads (one-time links) due to a non-atomic check-then-increment

Fingerprint `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:get_download_payload:non-atomic-download-count`

get_download_payload loads meta, checks download_count against max_downloads, increments, saves with an unconditional write, then reads the payload and applies auto_delete. Nothing locks or compares-and-swaps between load (145) and save (165), so two concurrent invocations for a max_downloads=1 transfer can both pass and both return the ciphertext, defeating the user-selected one-time guarantee for parallel requests. It is dominated by the presigned download bypass on S3 deployments and matters mainly for small files on the direct path and for memory/disk modes; likely low severity once validated.

**Claimed root cause.** The download limit is a read-modify-write on a JSON metadata object with no atomic conditional update, lock or version check.

### Trace

1. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Transfers.py:168` (entrypoint, Routes__Transfers.download__transfer_id): Unauthenticated GET; calls get_download_payload (181); download_base64 (206) likewise.
2. `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:145` (propagation, Transfer__Service.get_download_payload): Reads a meta snapshot.
3. `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:157` (propagation, Transfer__Service.get_download_payload): Limit check against the stale snapshot.
4. `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:165` (propagation, Transfer__Service.get_download_payload): Unconditional save_meta (last writer wins).
5. `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:167` (sink, Transfer__Service.get_download_payload): Returns payload to every racer; auto_delete (169-172) runs after the read.

### Evidence

- `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:31`: save_meta is a plain file__save.
- `sgraph_ai_app_send/lambda__user/storage/Storage_FS__S3.py:85`: In-repo S3 file__save calls file_create_from_bytes with no conditional-write or version parameters.
- `sgraph_ai_app_send/lambda__user/service/Transfer__Service.py:169`: auto_delete depends on the racy count and runs after the read.
- `sgraph_ai_app_send/lambda__user/schemas/Schema__Transfer.py:20`: max_downloads is a client-chosen access-limiting control.

### Blockers

- Whether the User Lambda permits concurrent invocations overlapping the load-to-save window.
- Whether memory-fs Storage_FS__Memory.file__save (not installed) performs any locking, and whether osbot-aws file_create_from_bytes (not installed) is a plain PutObject.
- S3 read-after-write timing between overlapping invocations.

### Resolution plan

- **Local (bounded):** With pinned deps and no network: in-memory transfer with max_downloads=1, auto_delete=True; two threads behind a threading.Barrier placed after load_meta (subclass adding only the barrier); observe both return payload bytes.
- **Owner-observed:** Owner-observed: reserved/provisioned concurrency of the User Lambda; deployed osbot-aws version backing Storage_FS__S3.file__save (unconditional PutObject?).

## Unvalidated vault file_id composed into storage keys allows '..' escape from the vault namespace

Fingerprint `sgraph_ai_app_send/lambda__user/storage/Storage__Paths.py:path__vault_payload:file_id-dot-segment-traversal`

Every vault pointer operation builds its storage key as f'{_ROOT}/vault/{vid[:2]}/{vid}/{file_id}/payload' (Storage__Paths.py:33-34). Only vault_id is validated (^[a-z0-9]{8,24}$); file_id comes unvalidated from the URL ({file_id:path}) on write/read/read-base64/delete and from the JSON body on batch (Service__Vault__Pointer.py:173, 250). A read-only batch needs no authentication (Routes__Vault__Pointer.py:180-185); a write/CAS/delete batch checks only the URL vault_id's write key, and first-write-wins lets any access-token holder own a fresh vault. If the storage backend resolves dot-segments: (a) an anonymous caller can read another vault's objects or a transfer payload (e.g. '../../../transfers/tt/tttt9999'), skipping the transfer status/expiry/max_downloads checks; (b) the owner of any vault can overwrite or delete another vault's objects/refs or a transfer payload. The asset is integrity and availability of other tenants' data and the transfer lifecycle (ciphertext confidentiality still rests on client keys). The sibling append service rejects the pattern with typed Safe_Str ids and traversal tests; the pointer service has neither. Escape depends on code not in the repo: the DISK backend subclasses upstream memory_fs Storage_FS__Local_Disk; the S3 backend passes the key literally (S3 does not normalise), so the Lambda/S3 path most likely stores a harmless literal key. deploy/aws/ec2.cfn.yml defaults StorageMode to disk, so disk-backed deployments are a documented default. The same file_id reaches presigned multipart keys via Service__Vault__Presigned.s3_key.

**Claimed root cause.** Service__Vault__Pointer and Storage__Paths.path__vault_payload put a caller-controlled file_id into a hierarchical storage key without rejecting '..', empty segments or a leading '/', and without checking that the result stays under {root}/vault/{vid[:2]}/{vid}/; authorization uses the URL vault_id only, so a normalising backend reads, writes or deletes keys outside that vault.

### Trace

1. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Vault__Pointer.py:167` (entrypoint, Routes__Vault__Pointer.batch__vault_id): POST /api/vault/batch/{vault_id}: only vault_id is validated; operations (with file_id) come from the body.
2. `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Vault__Pointer.py:183` (propagation, Routes__Vault__Pointer.batch__vault_id): All-read batches go to service.batch_read with no token or write-key check.
3. `sgraph_ai_app_send/lambda__user/service/Service__Vault__Pointer.py:165` (propagation, Service__Vault__Pointer.batch): Write batches check only the URL vault_id's manifest (first-write-wins).
4. `sgraph_ai_app_send/lambda__user/service/Service__Vault__Pointer.py:173` (propagation, Service__Vault__Pointer.batch): file_id = op.get('file_id','') passed unvalidated to vault_payload_path.
5. `sgraph_ai_app_send/lambda__user/service/Service__Vault__Pointer.py:44` (propagation, Service__Vault__Pointer.vault_payload_path): Delegates to path__vault_payload(vault_id, file_id).
6. `sgraph_ai_app_send/lambda__user/storage/Storage__Paths.py:34` (sink, path__vault_payload): Interpolates file_id verbatim; the key goes to storage_fs.file__save/file__bytes/file__delete (Service__Vault__Pointer.py:181,195,257).

### Evidence

- `sgraph_ai_app_send/lambda__user/fast_api/routes/Routes__Vault__Pointer.py:21`: {file_id:path} routes typed as plain str.
- `sgraph_ai_app_send/lambda__user/service/Service__Vault__Pointer.py:21`: VAULT_ID_PATTERN applies to vault_id only.
- `sgraph_ai_app_send/lambda__user/service/Service__Vault__Pointer.py:250`: batch_read takes file_id from the anonymous body.
- `sgraph_ai_app_send/lambda__user/storage/Storage__Paths.py:19`: Transfer payloads share the _ROOT tree, reachable with three '..' segments.
- `sgraph_ai_app_send/lambda__user/storage/Storage_FS__Local_Disk.py:3`: DISK backend subclasses upstream memory_fs Storage_FS__Local_Disk (join not in repo).
- `sgraph_ai_app_send/lambda__user/storage/Storage_FS__S3.py:40`: S3 backend uses the path as a literal key.
- `sgraph_ai_app_send/lambda__user/storage/Send__Config.py:69`: DISK mode selected by SEND__STORAGE_MODE=disk or SEND__DISK_PATH.
- `deploy/aws/ec2.cfn.yml:42`: EC2 template defaults StorageMode to disk and mounts /var/lib/sg-send at /data (line 211).
- `sgraph_ai_app_send/lambda__user/service/Service__Vault__Presigned.py:40`: Variant: presigned S3 keys built from the same unvalidated file_id.
- `tests/unit/lambda__user/service/test_Service__Vault__Append.py:639`: Sibling append service has typed traversal rejection with tests.

### Blockers

- Whether upstream memory_fs Storage_FS__Local_Disk resolves '..' when joining root_path and key (not installed) — decides the DISK escape.
- Whether osbot-utils Safe_Str__File__Path (applied by @type_safe) rejects, strips or keeps '..' (not installed); if it sanitises, the trace is refuted for every backend.
- Whether osbot_aws/botocore alter dot-segment keys in S3 mode (expected not).
- Which storage mode each real deployment uses.
- For URL variants only: whether the ASGI/HTTP stack passes literal or %2e%2e segments into {file_id:path}; the JSON batch variant is independent.

### Resolution plan

- **Local (bounded):** In an offline sandbox with pinned osbot-utils, memory-fs and osbot-fast-api from a vetted local wheel cache: create Storage_FS__Local_Disk(root_path=<scratch tmpdir>) and Service__Vault__Pointer on it; seed path__vault_payload('bbbb2222','bare/refs/ref-main') and path__transfer_payload('tttt9999') with dummy bytes; call batch_read('aaaa1111', [{'op':'read','file_id':'../../bb/bbbb2222/bare/refs/ref-main'}]) and the transfer variant; call batch('aaaa1111', [{'op':'write','file_id':'../../bb/bbbb2222/bare/refs/ref-main','data':'eA=='}], 'k1') and check the victim key; repeat with Storage_FS__Memory; print Safe_Str__File__Path('a/../b'). Dummy ids only.
- **Owner-observed:** Owner reports SEND__STORAGE_MODE/SEND__DISK_PATH per environment (Lambda config, EC2 stack StorageMode, Docker). For S3-backed environments, list whether any key under {root}/vault/ contains '/../' (literal storage).
