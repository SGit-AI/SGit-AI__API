# 03 — Implementation Plan

Seven steps, each gated. **Do not start the next step until the current gate passes.** Steps 0–1 need no decisions; step 2 needs D1–D3; step 5 needs D4–D5; step 7 needs D6–D9.

Escalate rather than improvise if: a test needs a behaviour change to pass, a vault-web feature turns out to need a Send route not covered by Q1/Q2, or the Lambda image measurement (step 5) is materially worse than today.

---

## Step 0 — Baseline (in `__Send`, no changes)

```bash
git rev-parse HEAD > BASELINE_SHA                                        # 5d50ae8 today
env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY SEND__STORAGE_MODE=memory \
  python -m pytest tests/unit/lambda__user tests/unit/utils -q            # record: 512 passed / 9 skipped today
npm run test:vault-unit && npm run test:vault-integration                # record counts
npx playwright test tests/e2e/vault_ui                                   # record counts (13 specs)
python -m pytest tests/integration/vault_ui/browser -q                   # incl. the sgit round-trip
# contract snapshot: the vault families + headers, as JSON
SEND__STORAGE_MODE=memory python3 - > BASELINE_CONTRACT.json <<'PY'
import json
from sgraph_ai_app_send.lambda__user.fast_api.Fast_API__SGraph__App__Send__User import Fast_API__SGraph__App__Send__User as A
a=A(); a.setup(); s=a.app().openapi()
print(json.dumps({p:sorted(m) for p,m in s['paths'].items() if p.startswith(('/api/vault','/api/info'))}, indent=1))
PY
VAULT_DEFAULT_ENDPOINT="" bash scripts/build-vault-static.sh /tmp/vaults-ui   # the tree step 4 commits
```

**Gate:** counts recorded; `BASELINE_CONTRACT.json` has 28 paths; `/tmp/vaults-ui` builds.

## Step 1 — Resolve `05` (Dinis)

D1–D10 and Q1–Q8 answered, or explicitly deferred with a default. **Gate:** `05__open-questions.md` has no row without an answer or a stated default.

## Step 2 — The repo (skeleton first, then the archive pointer)

- Rename `SGit-AI__API` → per D1 (GitHub keeps redirects; update `pyproject`, CI env `PACKAGE_NAME`, Pages links).
- Lay down the layout in `02` §1 with empty packages; CI green on the skeleton (tests → tag keeps working; **CI test job sets `SEND__STORAGE_MODE=memory` / `VAULTS__STORAGE_MODE=memory` explicitly** — the config auto-selects S3 when AWS credentials are present, which will bite the moment OIDC is added).
- README gets its first section: where the history lives (`__Send` @ `BASELINE_SHA`, the paths in `01`).

**Gate:** CI green; reality doc in this repo updated to say "skeleton, nothing moved yet" with the new names.

## Step 3 — The API

Per `01` §1.1: copy, rename, re-wire, trim. Only vault routes registered. `versions()` keyed by the new package name. Env aliases per ADR-7. Tests per `01` §1.3 with import paths updated; the route-list assertion reduced to the vault families **and reviewed line by line against `BASELINE_CONTRACT.json`**.

```bash
python -m pytest tests/unit -q                       # gate A: same pass count as step 0 for the moved subset, no new skips
python3 - <<'PY'                                     # gate B: the contract, path for path, method for method
import json
from sgit_vaults.api.Fast_API__Vaults import Fast_API__Vaults as A
a=A(); a.setup(); s=a.app().openapi()
new={p:sorted(m) for p,m in s['paths'].items() if p.startswith(('/api/vault','/api/info'))}
assert new==json.load(open('BASELINE_CONTRACT.json')), 'contract drift'
PY
grep -rn "sgraph_ai_app_send\|lambda__admin\|Transfer__Service" sgit_vaults/ && echo "LEAK" || echo "clean"
sgit clone --base-url http://127.0.0.1:<port> ...    # gate C: a real sgit push + clone against Vaults__Test_Server
```

**Gate:** A, B, C all pass. Record in `05` anything that had to be *changed* (not renamed) to pass — there should be nothing.

## Step 4 — The vault web

Commit `/tmp/vaults-ui` (from step 0, rebuilt from `BASELINE_SHA`) as `sgit_vaults__ui/`. Move `generate_vault_i18n_pages.py` and the build-info injection into `sgit_vaults__ui/build/`. Move the UI test suites and `package.json` scripts; point them at the flat tree. Container app serves `sgit_vaults__ui/` directly (no build step in the Dockerfile).

**Gate:** `test:vault-unit`, `test:vault-integration`, Playwright e2e (13 specs), browser integration (sgit round-trip) — same counts as step 0. `grep -rn "dev.send.sgraph.ai" sgit_vaults__ui/` is empty. No file inside `_common/js/components` or `_common/js/lib` differs from the step-0 build output (`diff -r`).

## Step 5 — One image, every target

- Dockerfile from `01` §1.4 without the overlay step. Build → `--network=none` memory-mode invariant (health + `/`) → publish to the registry (Q4) on tag.
- Lambda (image) via `deploy/aws/cfn/lambda.cfn.yml` into the account from Q3; **measure** cold start / p50 vs today's zip (ADR-4 gate). Fargate and EC2 via `deploy-full-cycle.yml` (first ever live run; OIDC role from Q3).
- Terraform modules (Q8 scope) reproducing the three CFN shapes; `terraform plan` clean in CI.
- Data: new bucket + root; one dry-run copy of the `vault/` prefix (D5); CloudFront function rewritten for the new root.

**Gate:** `test_smoke__deployed_target.py` 8/8 against Docker, Lambda, Fargate, EC2; full-cycle run green including teardown; Lambda measurement recorded and within the ADR-4 bound (or the zip optimisation kept and documented).

## Step 6 — Docs and the README test

Write `docs/` per `01` §1.5; regenerate the deploy vault from it; update `pages/llms.txt`. Then **run the README test for real** (`04` §2): a fresh Claude Code session or a colleague, README only, no `__Send` access. Every point where they guess or ask is a defect; fix, re-run.

**Gate:** README test passes with zero questions on Docker **and** on one cloud target.

## Step 7 — Cutover

- DNS: `dev.vaults.sgit.ai` → the dev stack; `vaults.sgit.ai` → main (Q5).
- Data copy for real (D5); old host read-only for the grace period.
- CLI: default base URL, `whoami` probe, `Vaults__Test_Server` import path — a CLI release (Q6).
- sgit.ai: `deploy/vault.json` → `ivpijuvg` on `vaults.sgit.ai`; embeds from `dev.vault.sgraph.ai` re-pointed (Q7).
- `__Send`: vault routes on `dev.send.sgraph.ai` 301 → `vaults.sgit.ai` for the grace period; `deploy-ui-vault.yml` disabled (not deleted); README pointer; reality docs (`infra`, `send-api`, `ui`) updated to say where the vault lives now; **nothing deleted**.
- This repo: reality doc → EXISTS; `vault/docs/status.md` milestone table; changelog entry classifying which tests should break (the CLI's default-host tests) and which must not (everything else).

**Gate:** vaults.sgit.ai serves the web and the API; a vault created on the old host opens on the new one; the CLI round-trip works against the new default; smoke green; the old host's vault routes redirect.

## Step 8 — Later, separate series (record now, do not fold in)

Deletion of the moved code from `__Send` (blocked by the admin→user `Routes__Info__SGraph` import); the vault-web quality pass (component renames, `sg-send.js` split); the native token registry (Explorer); removal of the `SEND__*` env aliases; retirement of the zip deployer if ADR-4's measurement allowed dropping it.

---

## Order at a Glance

```
0  baseline in __Send            ── counts, contract JSON, flattened UI tree
1  decisions (05)                ── D1–D10, Q1–Q8
2  repo skeleton + rename        ── CI green, archive pointer
3  API                           ── gates: tests, contract diff, leak grep, sgit round-trip
4  vault web (flattened)         ── gates: UI suites, no dev.send host, no component edits
5  one image, every target       ── gates: smoke ×4, full cycle, Lambda measurement, Terraform plan
6  docs + README test            ── gate: zero questions, Docker + one cloud target
7  cutover                       ── gates: DNS, data copy, CLI release, redirects, reality docs
8  later series                  ── deletions, quality pass, token registry, alias removal
```

*Released under CC BY 4.0.*
