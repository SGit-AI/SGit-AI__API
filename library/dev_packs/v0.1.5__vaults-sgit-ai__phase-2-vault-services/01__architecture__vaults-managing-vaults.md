# 01 — Architecture: vaults managing vaults

PROPOSED throughout. The model, then each service, then what it costs. Every placement is a claim to be contested; the questions are in `02`.

---

## 1. The model

```
                         a vaults.sgit.ai DEPLOYMENT (one image, one keypair)
   ┌───────────────────────────────────────────────────────────────────────────────────────┐
   │  boot:  private key  ──▶ opens the SUPPORTING VAULTS it was told about (ids + read keys) │
   │                                                                                       │
   │  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌────────────────┐  │
   │  │ credentials     │   │ secrets         │   │ config / kv     │   │ telemetry      │  │
   │  │ vault           │   │ vault           │   │ vault           │   │ vault          │  │
   │  │ API keys as     │   │ what THIS deploy│   │ feature flags,  │   │ one record per │  │
   │  │ records; lanes  │   │ needs: bucket,  │   │ limits, hosts   │   │ time bucket,   │  │
   │  │ for issue/revoke│   │ upstream keys   │   │                 │   │ over a lane    │  │
   │  └────────┬────────┘   └────────┬────────┘   └────────┬────────┘   └───────┬────────┘  │
   │           │ read (+append)      │ read                │ read               │ append     │
   │  ─────────┴─────────────────────┴─────────────────────┴────────────────────┴─────────  │
   │                         the vault API (phase 1, unchanged)                             │
   │  /api/vault/*  /api/vault/append/*  /api/vault/presigned/*  /api/info/*  /mcp          │
   │  ─────────────────────────────────────────────────────────────────────────────────────  │
   │                         the APPS endpoints (phase 2, new, thin)                        │
   │  /api/apps/keys/*      /api/apps/kv/*      /api/apps/secrets/*      (ciphertext only)  │
   └───────────────────────────────────────────────────────────────────────────────────────┘
        ▲ callers: sgit CLI, vault web, agents (MCP), other deployments — PKI-signed requests

   The supporting vaults are ordinary vaults. They can live on this deployment, on another
   vaults.sgit.ai, or on a static host (read-only ones). Nothing in the API knows which.
```

Three properties make this safe enough to be the default:

1. **The deployment holds one secret** (its private key). Everything else is a vault it can *read* because it was given a read key, or *append to* because it was given an append token. Losing the box loses one key; rotating the box is re-issuing one key.
2. **The apps endpoints return ciphertext.** They are projections over vault files at computed paths. The server never decrypts a record; the caller does, with a key it already holds. So an apps endpoint is not a new capability — it is a *shorter path* to an existing read. The only attack surface it adds is **enumeration and timing**, which is why it is PKI-gated (§5) and why it must not become an existence oracle (§3).
3. **Auth mode 3 is the same loop.** "Is this access token valid?" becomes "does the credentials vault hold a live record at the path this token computes to?" — no Send Admin Lambda, no separate store.

## 2. The supporting vaults (what each holds, who writes it)

| Vault | Holds | Written by | Read by | Notes |
|---|---|---|---|---|
| **credentials** | API-key *records* `{account, scope, budget, expiry, status}` at `keys/<H(key)>.json`, plus an `issued/` and `revoked/` lane | the operator (`sgit` or the dashboard) via write key; issuers via an append lane; revocation = a signed append | the deployment (read key) | The 08/06 "credential ≠ address" design, minus billing. `H(key)` is the file name so the *key itself* never lands in storage keys — the lesson of the raw-append-token finding |
| **secrets** | what the deployment needs to run: bucket name, region, upstream provider keys, the read keys of the other supporting vaults | the operator only | the deployment | Replaces N environment variables with one: `VAULTS__SECRETS_VAULT=<id>:<read-key>` (or just the id, if the read key is derived from the deployment's own keypair — Q3) |
| **config / kv** | feature flags, limits, allowed hosts, per-tenant settings | operator; later, apps via `/api/apps/kv` with a write key | the deployment; apps | A KV store is a vault with a flat tree and a naming rule — nothing more is needed |
| **telemetry** | one record per (channel, time bucket) — reads, writes, bytes, status classes — never per request | the deployment, over an append lane, one token per channel per day | operators, dashboards | The 09/07 design; the 22 Feb incident is the reason it is *not* per request |
| **backup** | zips of the supporting vaults (and, optionally, of tenant vaults on request) | the rotation job | restore drills | `/api/vault/zip` + `sgit export` exist; the schedule does not |

## 3. The apps endpoints

Thin FastAPI routes, one `Routes__Apps__*` class each, mounted on the phase-1 app. Each one is: **verify signature → compute path → read ciphertext from the named supporting vault → return it**. No decrypt, no write except through existing lanes.

| Endpoint | Does | Backed by | Gate |
|---|---|---|---|
| `GET /api/apps/keys/check` | returns the ciphertext record for the caller's key (or 404) — the caller decrypts and checks `status`/`expiry`/`budget` | credentials vault, path = `keys/<H(key)>` | signed request; the key itself travels only as its hash |
| `POST /api/apps/keys/issue`, `/revoke` | append a signed record to the `issued/` or `revoked/` lane; the operator's job materialises it into `keys/` | append lane | append token (issue) / write key (revoke) |
| `GET /api/apps/kv/<name>` | ciphertext of `kv/<name>` | config vault | signed request + read key the caller already has |
| `PUT /api/apps/kv/<name>` | write through to the config vault | config vault | write key (existing semantics) |
| `GET /api/apps/secrets/<name>` | ciphertext of `secrets/<name>` | secrets vault | signed request from a principal listed in the secrets vault's `acl.json` |

**The oracle rule.** `keys/check` returning 404 vs 200 *is* an existence signal for `H(key)`. That is acceptable **only** because the caller must sign the request with a registered key (§5), so the signal is available to identified principals, never to the public. The append gates keep their uniform 403 (09/08 decision). `kv` and `secrets` reads must return the same status for "absent" and "not yours" to a principal without rights.

**What this is not.** Not a secrets *manager* with versions, leases and audit (that is a product; this is a projection). Not a KV *database* (no queries, no ranges — a flat tree at computed names). Not billing.

## 4. The three auth modes, made explicit

| Mode | Set by | Check | Exists? |
|---|---|---|---|
| 0 — open | nothing set | every route open (the deploy README must shout this) | yes |
| 1 — single key | `VAULTS__ACCESS_TOKEN` (alias of `SGRAPH_SEND__ACCESS_TOKEN`) | header equals env | yes |
| 2 — delegated to a server | `…ADMIN__BASE_URL` | remote `token_lookup` (today: Send's Admin Lambda) | yes (transitional in phase 1) |
| **3 — vault-backed** | `VAULTS__CREDENTIALS_VAULT=<id>` (+ how to read it, Q3) | read `keys/<H(token)>` from the credentials vault, decrypt with the deployment's key, check status; positive cache TTL as today | **new** — phase 2, step 2.1 |

Mode 3 replaces mode 2's *hosted* use and is what makes a fleet of deployments share one credentials vault (or each have its own) with no shared server. `Service__Access_Token` already has the shape; mode 3 is a second `check()` branch and a `Vault__Reader` that opens a vault with a read key from inside the API — the first time the server *reads* a vault as a client. That is the one genuinely new primitive in this pack.

## 5. PKI-signed requests

- **Identity**: an agent or site has a keypair (`sgit keygen` exists; pki.sgit.ai and the admin `/keys/*` prototype publish public keys). A deployment has one too.
- **Registry**: a `principals/` folder in the credentials vault: `principals/<fingerprint>.json` = public key + scopes + status. Enrolment and revocation are signed appends (P-ENR-002/003 as designed).
- **Signature**: `X-SGit-Principal: <fingerprint>`, `X-SGit-Signature: <ECDSA-P256 over (method, path, body-hash, timestamp)>`, `X-SGit-Timestamp`. Verify: principal is in the registry and live; signature valid; timestamp within a window; (optional) nonce cache. This is the Feb `admin-pki-mtls` plan's ECDSA half, without mTLS.
- **Where it gates**: the apps endpoints (always); `/api/vault/*` writes (optionally, as a stronger alternative to the access token — mode 4, later).
- **What it does not do**: encrypt anything (that is the vault key's job), or replace the write key (which stays the vault-level capability).

## 6. Rotation and backup as orchestration

- **What can rotate**: access tokens (records in the credentials vault: issue new, revoke old — the token is a *record*, not an address); principals' keys (same); append tokens (re-`configure`, exists); share tokens (exists); the deployment's own keypair (re-issue + re-share the supporting vaults' read keys to it).
- **Vault keys rotate with `sgit vault move`** (Dinis, 4 Oct: prefer it over `rekey`, which wipes and re-inits). `move` re-keys a vault into a new id **keeping its history**, in eight steps with a sentinel commit recording the reason, `--dry-run` to rehearse, `--cleanup` to finish or roll back a half-done move, and `--to` to land it on another server. The new id must still be re-shared to every holder of the old key or read key, so rotation is a re-share event; schedule it weekly only for vaults whose readers are machines you control (the supporting vaults), and on demand for tenant vaults.
- **The job**: a scheduled workflow (GitHub Actions cron in the deployment's repo, or a Lambda on a schedule) that runs `sgit` against the supporting vaults: issue → publish → revoke-after-grace, then `sgit export` of each supporting vault into the backup vault, then a **restore drill** (clone the backup, open it, compare). Weekly is fine; the drill is the point.
- **The invariant**: every rotation is a commit in a vault, so the history *is* the audit log.

## 7. Observability without plaintext

Adopt the 09/07 design as written: the API appends **one record per (channel, bucket)** to the telemetry lane — counts of reads/writes/bytes/status classes per vault id prefix, never file ids, never client identifiers beyond a hashed principal. A completed bucket is processed once. The dashboard (a vault app) reads the telemetry vault. CloudFront logs stay where they are; if they are ever wanted, LETS is the design. This also produces, within a few weeks, the **usage data the memo wants for pruning routes** — the honest order is observe, then prune.

## 8. Deployment for agents, humans and CI

- **Phase 1 gives**: one image; `docker run`; CFN for Lambda/EC2/Fargate; Terraform; the README test.
- **Phase 2 adds**: `sgit deploy <target>` (or a `deploy/` script the README already documents) that on first boot **creates the supporting vaults**, seeds the secrets vault, prints the deployment's public key, and writes a `deployment.json` back into the operator's vault — so a new region is: run it, escrow the key, done.
- **The ephemeral deploy server** (03/10 design): a Router Lambda that boots an EC2 on demand, runs the deploy, zips the resulting state into a vault, and terminates. Worth doing *after* `sgit deploy` exists, as the same script under a different trigger — and yes, our own CI is the first customer: a pipeline run that leaves behind a vault is a pipeline run an agent can read later.

## 9. Costs and honest tensions

| Tension | Note |
|---|---|
| The server now reads vaults as a client | New primitive, new trust: the deployment holds read keys. Keep them in the secrets vault, opened by the one private key; never in env beyond bootstrap. |
| Apps endpoints vs "no new surface" | They add enumeration/timing surface, gated by PKI. If PKI is not done first, do not ship them. |
| "Only features we use" vs no data | Observability first (§7), pruning second. Anything else is guessing. |
| Vault-backed auth on a cold Lambda | A read of a computed path per uncached token check; with the TTL cache that is one S3 GET per minute per token. Acceptable; measure. |
| Phase 1 discipline | None of this touches phase 1's contract. It mounts beside it. If a phase-2 change needs a phase-1 route to change, that is a red flag. |

*Released under CC BY 4.0.*
