# Dev Pack: vaults.sgit.ai — The Villager Transformation of the Vault Platform

**version** v0.1.5 (SGit-AI__API tag; origin `__Send` at v0.33.69) · **date** 30 September 2026
**for** the Villager team (restarted by this pack) — a fresh Claude Code session doing the work should assume no prior context
**source memo** Dinis Cruz, voice, 30 Sep 2026 (restated in `team/humans/dinis_cruz/claude-code-web/09/30/v0.1.5__memo-response__vaults-sgit-ai-the-villager-transformation.md`)
**supersedes** `v0.33.59__sgit-api-extraction` (16 Aug) — that pack's *evidence* (the clean cut, the couplings, the gates that hold) carries over; its *discipline* (move with zero changes, identical zip) does not, because the ask has changed
**status** PROPOSED — nothing here is implemented

---

## Read These In Order

| # | File | What it gives you |
|---|---|---|
| **00** | this file | orientation, the governing discipline, what is decided and what is not |
| **01** | `01__scope-and-manifest.md` | what moves, what is transformed on the way, what stays, the five couplings to sever |
| **02** | `02__architecture-and-decisions.md` | target layout, deployment topology, ADRs |
| **03** | `03__implementation-plan.md` | seven gated steps |
| **04** | `04__verification-and-acceptance.md` | the parity proof, the README test, acceptance, rollback |
| **05** | `05__open-questions.md` | decisions D1–D10 and questions Q1–Q8 — resolve before step 2 |
| — | `maps/vaults-sgit-ai__evolution.mmd` | the evolution map (Mermaid `wardley-beta`) — the Villager Cartographer's living map from here on |

---

## The Governing Discipline

> **Same features, new shape. Parity is proven by the existing tests, not by diffing artefacts.**

The August pack proved a *move* by comparing zip members. This pack proves a *transformation* by running the same behaviour tests against the new home: the vault API unit suite (in-memory, no mocks), the vault-web unit/integration/e2e suites, the contract test (route list + headers), and a real `sgit` round-trip. If those pass unchanged, the features are the same. That is the Villager's proof, and it is the only one that survives a rename, a re-layout, and a fresh history.

Three rules that follow from it, all Villager rules:

1. **No behaviour change.** Route paths, methods, status codes, headers, response bodies (one exception: the package name in `/api/info/versions`, ADR-2), storage semantics. A bug that needs a behaviour change is recorded and sent to Explorer, not fixed here.
2. **Transform the *shape* freely.** Package names, file layout, build steps, deploy artefacts, configuration surface, docs — all in scope, because none of them are behaviour.
3. **Sever couplings by configuration where the code already allows it; record the rest.** Two of the five couplings to Send (auth mode, endpoint defaults) are already configurable. The other three (share tokens, public previews, the S3 path root) need a decision each (`05`).

---

## What Has Already Been Decided (from the memo — do not relitigate)

1. **The boundary is the vault**, not the User Lambda's reachable set. Transfers, presigned-transfers, early-access and public-preview stay in `__Send`. "Keep the send stuff where it is."
2. **The vault web moves with the API**, as one product, one image, one repo.
3. **The home is the sgit domain**: `vaults.sgit.ai`. Away from `sgraph.ai`.
4. **Fresh history.** Only the materials needed; `__Send` is the archive.
5. **Own deploy artefacts**: Docker image, Lambda, CloudFormation, Terraform.
6. **The audience is the next generation of sgit users.** The README test is the acceptance criterion.

## What Is Not Decided (needs Dinis — see `05`)

D1 repo name · D2 package name · D3 history (fresh, confirmed above; the *pointer* wording is open) · D4 Lambda artefact (container vs zip) · D5 existing vault data · D6 hosted auth · D7 UI clean-up depth · D8 fate of `__Send`'s joint image · D9 domains and CLI default · D10 team.

Plus eight questions (Q1–Q8) that need a human action or a product answer, chief among them **whether read-only share tokens and public previews count as vault features** (they are transfer-backed today).

---

## What The Investigation Established (evidence, 30 Sep 2026)

| Finding | Consequence |
|---|---|
| The vault API surface is 28 of the User app's 47 OpenAPI paths (pointer 13, append 6, presigned 4, info 5) plus `/mcp`, docs and 3 `.well-known` stubs | The API cut is a subset of what the August pack already proved clean (42 modules, 0 admin, 0 UI) |
| The sgit CLI (PyPI 0.16.0) consumes 12 vault paths + `/api/info`; it also probes `/api/auth/whoami`, which does not exist | Contract to freeze = those 12 + info; tell the CLI team about `whoami` |
| The vault web (v0.2.3) is 178 files, ~34k lines JS, 72 components — plus 108 files overlaid **at build time** from the Send user UI (`_common` v0.3.0–v0.3.3), including `send-browse`, which is the vault file browser | The "clean UI" is mostly a *flattening*: commit what the build script produces, drop the overlay machinery |
| The vault web hard-codes `https://dev.send.sgraph.ai` in 8+ files; the build script rewrites it | Same-origin by default is a build-time transformation the repo already performs |
| Vault web → Send couplings: RO share tokens (`deriveRoTokenTransferId` → `/api/transfers/download`), `check-token` (Send admin tokens), public previews (`sg-link-card`) | Q1/Q2 in `05` — product decisions, not engineering ones |
| Hosted auth = Admin Lambda token lookup; self-host auth = env single key; both exist in `Service__Access_Token` | D6: no code needed for either mode |
| S3 root is `sg-send__data/sg-send-api__v1.0/shared/vault/…`, duplicated in the CloudFront immutable-bypass function | D5: data copy + new root is a deploy-time choice; the edge function must follow |
| Deployments today: zip Lambda (live), container image (works, Docker Hub), CFN (lint-clean, never run), Terraform (none) | D4; Terraform is net-new work |
| The Villager team has produced nothing since 25 Feb; its Cartographer never drew a map; `.claude/villager/CLAUDE.md` is stale | D10; this pack is the first real handover brief the team has had |

---

## The Success Criterion

> **Can somebody who has never seen this code deploy their own vault server from the new repository, following only its README, point `sgit` at it, push a vault, and open it in the browser — without asking anybody a question?**

`04` turns it into a checklist. It is the same criterion as the August pack, with the vault web and the `sgit` round-trip added, because that is what "use sgit myself" means.

---

## Scope Boundary — What This Pack Does NOT Cover

- **A native token registry** in the vault API (severing the last Send dependency for hosted auth) — Explorer follow-up, recorded in `05`.
- **Renaming `send-*` components and splitting `sg-send.js`** inside the vault web — the first Explorer-free quality pass after cutover (D7).
- **Static clone in the CLI** — CLI team; this repo's pinned conformance test flips when it ships.
- **Deleting the moved code from `__Send`** — a later series, per the August discipline (record, do not delete).
- **GCP Terraform, Heroku CI** — documented commands stay documented commands until a second consumer needs a module.

*Released under CC BY 4.0.*
