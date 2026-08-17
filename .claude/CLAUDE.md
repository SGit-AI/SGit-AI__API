# SGit-AI API — Agent Guidance

**Read this before starting any task.** This file is the single source of truth for all agents and roles working on the SGit API repository.

---

## MEMORY.md Policy

**Do NOT use MEMORY.md** (the auto-memory at `~/.claude/projects/.../memory/MEMORY.md`). All persistent project knowledge is maintained by the Librarian in the repo itself. If you need to record something, add it to the appropriate location in `team/roles/librarian/` or request the Librarian to update the relevant docs.

---

## Reality Document — MANDATORY CHECK

**Before describing, assessing, or assuming what this repo can do, READ the reality document in:**

`team/roles/librarian/reality/`

This is the **code-verified** record of what actually exists here. As of the repo bootstrap, this repository contains **scaffolding only — no API code has been moved yet.** The SG/API extraction from `SGraph-AI__App__Send` is planned, not done.

### Rules (Non-Negotiable)

1. **If the reality document doesn't list it, it does not exist.** Do not describe proposed features as if they are shipped.
2. **Proposed features must be labelled.** If you describe something not in the reality document, you MUST write: "PROPOSED — does not exist yet."
3. **Briefs are aspirations, not facts.** The extraction dev pack describes what WILL move here, not what HAS moved.
4. **Update the reality document when you change code.** Same commit.

---

## Project

**SGit API** — the server side of the sgit protocol: the deployable API service consumed by the `sgit` CLI (PyPI: `sgit-ai`) and the vault web UI. Extracted from [`SGraph-AI__App__Send`](https://github.com/the-cyber-boardroom/SGraph-AI__App__Send) (the User Lambda's reachable set).

**The extraction dev pack** lives at `library/dev_packs/v0.33.59__sgit-api-extraction/` — read files 00→05 in order before doing any extraction work. Its governing discipline: **move with zero changes, verify with the identical-output test, delete in a separate series afterwards.**

**Contract rule:** the API contract with the sgit client and vault web (all `/api/vault/*`, `/api/transfers/*`, `/api/presigned/*`, `/api/info/*`, `/mcp` routes; auth headers `x-sgraph-access-token`, `x-sgraph-vault-write-key`, `x-vault-read-key`, `x-vault-enum-key`, `x-vault-public`) must not change during or after the move.

**Version file:** `sgit_ai_api/version` — **owned exclusively by the CI pipeline.** Do not read it, write it, or reference it in commit messages. CI increments it automatically after tests pass.

---

## Stack

| Layer | Technology | Rule |
|-------|-----------|------|
| Runtime | Python 3.12 / arm64 | |
| Web framework | FastAPI via `osbot-fast-api` / `osbot-fast-api-serverless` | Use `Serverless__Fast_API` base class |
| Lambda adapter | Mangum (via osbot-fast-api) | |
| Storage | Memory-FS (`Storage_FS`) | Pluggable backends: memory, disk, S3 |
| AWS operations | `osbot-aws` | **Never use boto3 directly** |
| Type system | `Type_Safe` from `osbot-utils` | **Never use Pydantic** |
| Testing | pytest, in-memory stack | **No mocks, no patches** |
| CI/CD | GitHub Actions | Test → tag (→ deploy, once code lands) |

---

## Repo Structure

```
sgit_ai_api/                     # Application code (currently: version + utils skeleton;
                                 #   the extraction will land the API service here)
tests/unit/                      # Tests (no mocks; in-memory stack once code lands)

.github/workflows/               # CI pipelines
  ci-pipeline.yml                # workflow_call base: run-tests → increment-tag
  ci-pipeline__dev.yml           # push to dev  → tests + minor tag bump
  ci-pipeline__main.yml          # push to main → tests + major tag bump

library/                         # Specs, guides, dev packs
  dev_packs/v0.33.59__sgit-api-extraction/   # THE extraction brief pack (00–05)

team/                            # Team structure (mirrors SGraph-AI__App__Send)
  roles/                         # Role-based review documents
    librarian/reality/           # Code-verified reality document
    {role}/reviews/MM/DD/        # Role review output
  comms/                         # Agent-to-agent communication
    changelog/MM/DD/             # Changelog entries for every UI/API-affecting change
  humans/dinis_cruz/
    briefs/                      # Human briefs (input — READ-ONLY for agents)
    debriefs/MM/DD/              # Team debriefs (agent output for human review)
    claude-code-web/MM/DD/       # Agent session outputs

.claude/CLAUDE.md                # This file
```

---

## Key Rules

### Code Patterns

1. **All schemas** use `Type_Safe` (from `osbot-utils`), never Pydantic
2. **All AWS calls** go through `osbot-aws`, never `boto3` directly
3. **All storage** goes through Memory-FS (`Storage_FS`), never direct filesystem or S3 calls
4. **All FastAPI apps** extend `Serverless__Fast_API` from `osbot-fast-api-serverless`
5. **All tests** use real implementations (in-memory Memory-FS), no mocks or patches
6. **Version prefix** on all review/doc files: `{version}__description.md` (version from the latest git tag — do NOT read the version file)

### Security

7. **Server never sees plaintext** — encryption happens in the browser/client; the server stores ciphertext only
8. **No decryption keys on the server** — keys stay with clients, shared out-of-band
9. **NEVER commit access tokens, vault keys, share tokens, or API keys to Git.** If one appears in a commit, it is a security incident. Use environment variables or out-of-band channels only.

### Human Folders — Read-Only for Agents

10. **`team/humans/dinis_cruz/briefs/` is HUMAN-ONLY.** Agents must NEVER create, modify, or move files in this folder. No exceptions.
11. **Agent session outputs** go to `team/humans/dinis_cruz/claude-code-web/MM/DD/`
12. **Debriefs** go to `team/humans/dinis_cruz/debriefs/MM/DD/`
13. **Role reviews** go to `team/roles/{role}/reviews/MM/DD/`

### Cross-Team Communication

14. **Every code change that affects the API** must have a changelog entry in `team/comms/changelog/MM/DD/`, classifying which tests SHOULD break (good failure) vs should NOT break (bad failure)

### Git

15. **Default branch:** `dev`
16. **Feature branches** branch from `dev`; naming: `claude/{description}-{session-id}`
17. **Always push with:** `git push -u origin {branch-name}`
18. **Pull from dev before starting work** — `git fetch origin dev && git merge origin/dev` at session start
19. **Merging `dev` → `main`** triggers the main pipeline (tests + major tag bump)
20. **NEVER touch `sgit_ai_api/version` or `pyproject.toml`'s version field** — CI owns both

---

## Role System

Same role system as `SGraph-AI__App__Send` — see that repo's `.claude/CLAUDE.md` for the full 18-role, three-team (Explorer / Villager / Town Planner) definition. This repository starts life as **Explorer territory** (the extraction) and graduates to **Villager territory** (multi-platform, multi-region production deployment) once the move is verified.

**Dinis Cruz** is the human stakeholder, decision-maker, and project owner. His briefs in `team/humans/dinis_cruz/briefs/` drive priorities.

Before starting work, check:
1. **Reality document** in `team/roles/librarian/reality/`
2. Latest human brief in `team/humans/dinis_cruz/briefs/` (highest-dated subfolder)
3. Latest debrief in `team/humans/dinis_cruz/debriefs/`
4. The extraction dev pack in `library/dev_packs/v0.33.59__sgit-api-extraction/`
5. Your role's previous reviews in `team/roles/{your-role}/reviews/`

---

## Current State

**Scaffolding only.** CI (unit tests + auto-tagging on dev/main) is live. The API code extraction from `SGraph-AI__App__Send` is the next piece of work — follow the dev pack's implementation plan (`03__implementation-plan.md`), noting the pre-move preparation already done in the origin repo (see the origin repo's `team/roles/dev/reviews/08/17/v0.33.61__review__sgit-api-extraction-pre-move-verification.md`).

**Success criterion for the extraction:** deployment of the SGit API via this repo's CI pipeline to multiple platforms and regions, and the README test — someone who has never seen this code deploys it from this repository, following only its README, without asking anybody a question.
