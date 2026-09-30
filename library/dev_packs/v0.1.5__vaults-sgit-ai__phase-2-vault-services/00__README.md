# Dev Pack (phase 2): Vault Services — vaults managing vaults

**version** v0.1.5 · **date** 30 September 2026 · **status** PROPOSED — a design brief, not an implementation plan
**source memo** Dinis Cruz, voice, 30 Sep 2026 (second memo of the day: "the next phase")
**for** the Explorer team, once phase 1 (`v0.1.5__vaults-sgit-ai`) has a repo to land in — and Dinis, for the decisions in `02`
**team** Explorer. Every item here is a *feature*; none of it belongs in the Villager pack. The two run in sequence (or in parallel on the new repo after step 1.2), never mixed in one commit.

---

## Read These In Order

| # | File | What it gives you |
|---|---|---|
| **00** | this file | the memo restated; what exists today vs what the memo assumes; the shape of the answer |
| **01** | `01__architecture__vaults-managing-vaults.md` | the model: supporting vaults, the "apps" endpoints, the three auth modes, PKI, rotation, observability, deploy |
| **02** | `02__decisions-and-questions.md` | what needs Dinis, what needs the CLI team, and the sequencing |

---

## The Memo, Restated

1. **Move the vault to the sgit domain, refactor, clean up** — phase 1, already in play.
2. **Think again about what the API should be, and keep only the features we actually use.** No usage data exists for any route (verified: analytics disabled, vault reads deliberately uninstrumented, no CloudFront log pipeline). Phase 1 keeps the surface verbatim; the pruning is a phase-2 act that first needs the observability below.
3. **A one-container, end-to-end deployment that works.** Phase 1 delivers the image; phase 2 makes it self-sufficient.
4. **Push complexity out of the Lambda and into vaults.** The API grew server-side logic (key management, admin token lookups) that could be a vault the API *reads*. Append lanes make this workable: asynchronous, blind-write, gate-checked.
5. **Three services most vaults need, offered by every deployment**: API-key management, a key-value store, secrets management — as **curated "apps" endpoints** that return only ciphertext, so they add no new capability to the server and (almost) no attack surface.
6. **PKI everywhere**: agents and sites now publish public keys, so requests can be identified and signed.
7. **Rotation and backup as a built-in orchestration** — ideally weekly — "a security model and an orchestration model by itself".
8. **Monitoring and observability** of vault traffic, because vaults are about to be sold and backed up.
9. **Three auth modes**: open (internal), single key via environment (exists), and **vault-backed via API** — the deployment's only secret is its own private key, which unlocks the vault(s) holding its secrets and its API-key registry, possibly on a different server.
10. **Deployment must be trivial for agents, humans and CI**: tens of vault deployments are coming; an ephemeral deploy server; "zip the vault at the end" — vaults as memory, including for our own CI.

## What Exists Today vs What the Memo Assumes (code-verified, 30 Sep)

| Memo assumes | Reality | Where |
|---|---|---|
| An API-key / credential service on vaults (issue, scope, budget, expiry, revoke, existence lookup) | **PROPOSED.** Design exists (08/06 "credential ≠ address": four vaults per customer, hot path holds only an append token; 05/14 credential-manager vault). Only shipped primitive: Admin Lambda access tokens on the non-prod admin | `__Send` briefs 08/06 vault-authorisation, 05/14; `reality/identity` |
| A deterministic "does this key exist" check | **Partly.** `GET /api/vault/health/{id}` (vault-level), 404 on `read` (file-level), batch read. The append gate deliberately returns 403 whether or not the vault exists — no existence oracle by design. Deterministic value / per-path indexes are PROPOSED | `Routes__Vault__Pointer.py`; 09/08 declared-mounts response |
| Server-side secrets / KV "apps" endpoints returning ciphertext | **None.** Secrets custody is browser-only (owner-secrets under `.vault/owner/secrets/`); `sgit secrets` and MCP `secrets_*` are PROPOSED; no KV product | `reality/vault`, `reality/cli` |
| PKI-signed requests + a registry of agent/site keys | **Partly.** `sgit keygen/sign/verify/encrypt/decrypt` exist (RSA-OAEP 4096 + ECDSA P-256, file-level); browser SecureChannel exists; an admin `/keys/*` registry prototype exists on non-prod. **No** signed-request verification on any API route, no revocation, no lane-from-public-key | `reality/identity/proposed/agent-enrolment.md` (P-ENR-*, P-KRG-*) |
| Rotation + backup orchestration | **None.** Vault-key rotation cannot exist (the key *is* the identity; only migration); access-token and share-token rotation exist; `/api/vault/zip` and `sgit export` exist; no scheduler, no restore drills (P-183–P-189 PROPOSED) | 08/14 "read keys yes, write keys never"; 05/16 backup brief |
| Vault traffic observability | **None.** `Middleware__Analytics` disabled since 22 Feb (65k-file incident); vault reads deliberately uninstrumented; LETS pipeline never built; 09/07 brief says "per-vault observability has never been specified" | Villager DevOps incident review; 09/07 logging brief |
| Three auth modes | **Two and a half exist.** Open, single env key, and *delegated to another server* (the Admin Lambda). A **vault-backed** delegate is the new one | `Service__Access_Token.check()` |
| Easy deploy for agents/humans/CI; ephemeral deploy server; zip at the end | **Partly.** Universal image + CFN + full-cycle workflow exist (BETA, never run live); Deploy Service (ephemeral EC2 + Router Lambda) PROPOSED since March; SG/Compute exists outside this repo; zip exists | `reality/infra`; 03/10 deploy-service brief |

**Net:** of the seven capabilities the memo names, one exists (auth modes), three exist as primitives without the service on top (existence check, PKI, zip), and three do not exist at all (key service, secrets/KV endpoints, observability). The memo is right that the *primitives* are now there; the work is the services.

## The Shape of the Answer (one paragraph; `01` has the detail)

A deployment of vaults.sgit.ai owns **one keypair**. With it, it opens a small set of **supporting vaults** — a *credentials* vault (API keys as records, written over an append lane, read by the deployment), a *secrets* vault (what the deployment itself needs: bucket names, upstream keys), and a *config/KV* vault — which may live on the same deployment, on another vaults.sgit.ai, or on a static host. Three **apps endpoints** (`/api/apps/keys`, `/api/apps/kv`, `/api/apps/secrets`) are thin, PKI-gated projections over those vaults that hand back ciphertext the caller decrypts; they add no server-side plaintext and no new storage. **Auth mode 3** is exactly this loop applied to the deployment's own access tokens: instead of asking the Send Admin Lambda, it asks its credentials vault. **Rotation** is a scheduled push of new records into the same lanes plus a zip to a backup vault; **observability** is a per-deployment append lane that receives one record per time bucket (the 09/07 design), never per request. **Deploy** is the phase-1 image plus a `sgit deploy` (or a Router-Lambda-fronted ephemeral server) that creates the supporting vaults as part of first boot.

## Boundaries

- **Not in this pack:** phase 1 (the move); anything that changes the phase-1 contract; payments/billing (its own PROPOSED family); the Chrome-extension secrets manager (09/05); pruning routes before the observability exists to justify it.
- **The one thing to refuse:** an existence oracle on append gates. The 09/08 response refused it deliberately; the key-existence check the memo wants must be a *read of a computed path in a vault the caller may read*, not a 200/403 difference on a lane.

*Released under CC BY 4.0.*
