# 04 — Verification and Acceptance

Two proofs carry this work: the **parity proof** (same features) and the **README test** (usable by a stranger). Everything else supports them.

---

## 1. The Parity Proof (gates on steps 3, 4, 5)

The August pack compared zip members. A transformation cannot be verified that way — the artefact is meant to differ. It can be verified by behaviour, and the behaviour tests already exist:

| Layer | Suite | Today (step 0) | Passes when |
|---|---|---|---|
| API | `tests/unit` (in-memory, no mocks): routes, services, storage, MCP mount, handler, test server | 512 / 9 skipped for the extraction-shaped suite; the vault subset is recorded at step 0 | same count for the moved subset, **no new skips** |
| API contract | `BASELINE_CONTRACT.json` vs the new app's OpenAPI (paths × methods for `/api/vault*`, `/api/info*`) | 28 paths | zero drift |
| API headers | the six header constants + CORS allow-list | verbatim | `grep` of the constants' values unchanged |
| Web | `test:vault-unit`, `test:vault-integration`, Playwright e2e (13 specs), browser integration incl. `test__sgit_round_trip` | recorded at step 0 | same counts |
| Web source | `diff -r` of `_common/js/{components,lib}` vs the step-0 flattened build | identical | identical (ADR-8: no component edits) |
| Protocol | `tests/conformance` (static-read suite, real `sgit` CLI) | 5 | 5 (flips to a full clone when the CLI ships static transport) |
| Deployed | `test_smoke__deployed_target.py` | 8/8 vs local container | 8/8 vs Docker, Lambda, Fargate, EC2 |
| End to end | `sgit init/commit/push/clone` against each deployed target; open the vault in the served web | — | round-trip on every target |

**Allowed differences, and nothing else:** import paths, package/module names, the `versions()` key, env variable *aliases* (old names still work), file layout, build steps, deploy artefact names, the S3 root (a deploy-time value). **Any assertion that needs editing to pass is a defect** — record it in `05` and escalate; do not edit the assertion.

## 2. The README Test (gate on step 6)

> **Can somebody who has never seen this code deploy their own vault server from the new repository, following only its README, point `sgit` at it, push a vault, and open it in the browser — without asking anybody a question?**

Run it as a test: a fresh Claude Code session with no context, or a colleague. README only; no `__Send`; no asking. Every guess or question is a documentation defect to fix before the step passes.

**Passes when:**

- [ ] Repo cloned; `docker run … ghcr.io/sgit-ai/vaults` reaches `/api/info/health` → `{"status":"ok"}` and `/` renders the vault web
- [ ] `pip install sgit-ai`; `sgit init` + `commit` + `push --base-url http://localhost:8080 --token …` succeed against it
- [ ] The pushed vault opens in the browser at `http://localhost:8080/#<vault-key>` (or the documented locale path)
- [ ] `sgit clone` of the same vault into a second directory yields identical files
- [ ] One cloud target deployed end to end from the documented commands (Lambda via CFN, or Terraform), `GET /api/info/health` on the public URL, the same round-trip against it
- [ ] `GET /api/openapi.json` lists the `/api/vault/*` routes; `/api/docs` renders
- [ ] Teardown documented and performed; the account is clean
- [ ] Zero questions asked

## 3. Overall Acceptance

| # | Criterion | Evidence |
|---|---|---|
| 1 | Repo contains exactly the manifest in `01` §1; nothing from `01` §2 | file listing; `grep -rn "sgraph_ai_app_send\|lambda__admin\|Transfer__Service" sgit_vaults/` empty |
| 2 | Parity proof (§1) passes at every layer | recorded counts, contract diff, source diff |
| 3 | The vault web has no reference to a `sgraph.ai` host | `grep -rn "sgraph.ai" sgit_vaults__ui/` empty (or only in documented outbound links) |
| 4 | One image, published on tag, runs on Docker, Lambda, Fargate, EC2 (Cloud Run and Heroku documented) | registry tag; full-cycle run; smoke 8/8 ×4 |
| 5 | Terraform reproduces the CFN shapes | `terraform plan` clean in CI; one live apply + destroy |
| 6 | Lambda image measured against the zip baseline; outcome recorded | numbers in `05` |
| 7 | Data: a vault copied from the old bucket opens on the new host unchanged | one real vault, before/after checksums of a clone |
| 8 | Hosted auth mode documented as transitional; self-host mode documented as the default | README + `docs/operations/` |
| 9 | README test passes with zero questions, Docker + one cloud target | tester's notes |
| 10 | History: fresh, with the archive pointer (`__Send` @ `BASELINE_SHA`, paths) in the README | README |
| 11 | Version bump reasoned as the rename (ADR-2) | release note |
| 12 | Reality docs updated in this repo **and** in `__Send` (`infra`, `send-api`, `ui`); deploy vault `status.md` and `scripts/README.md` no longer point at `__Send` for deployment code | diffs in both repos |
| 13 | Changelog entry classifies test impact (which tests SHOULD break: the CLI's default-host tests; which must NOT: everything else) | `team/comms/changelog/09/…` |
| 14 | Nothing deleted from `__Send`; the disabled workflow and the redirect are in place | workflow diff; a `curl -I` of an old vault URL |
| 15 | Deletion candidates and follow-ups recorded (`05` §3), **nothing done** | file exists, non-empty |

## 4. Rollback

- **Before step 7:** `__Send` is untouched and still serves everything. Abandon or pause the new repo; nothing to undo.
- **Step 7, before the old host stops:** DNS back; the old User Lambda still has the vault routes; the CLI's `--base-url` overrides the default. Data copied, not moved, so the old bucket is intact.
- **After the grace period:** the new host is the only one; rollback is a redeploy of the old User Lambda from `__Send` at `BASELINE_SHA` and a reverse data copy. Keep `BASELINE_SHA` deployable until the first release *after* cutover has been in production for a full cycle.

## 5. What "Done" Does Not Include

The native token registry, the vault-web quality pass, deletions in `__Send`, static clone in the CLI, GCP Terraform. Steps 8 and later packs.

*Released under CC BY 4.0.*
