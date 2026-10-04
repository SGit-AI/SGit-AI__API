# Reality Document — SGit-AI__API

**Code-verified record of what exists in this repository.**
Rule: if it is not listed here, it does not exist. Anything described elsewhere that is not
here must be labelled "PROPOSED — does not exist yet."

**Last verified:** 2026-09-30 (code unchanged since 18 Aug; docs/packs added — see Docs table)

---

## EXISTS

### Code

| Item | Location | Notes |
|---|---|---|
| Package skeleton | `sgit_ai_api/` | `package_name`, `path`, version file |
| Version utility | `sgit_ai_api/utils/Version.py` | Type_Safe class reading `sgit_ai_api/version` |

### Tests

| Item | Location | Notes |
|---|---|---|
| Version tests | `tests/unit/test_Version.py` | 3 tests |
| Package tests | `tests/unit/test__sgit_ai_api.py` | 3 tests |
| **sgit parity gate** | `tests/regression/` (scenarios, conftest, test) + `.github/workflows/regression-parity.yml` | 5 invariant tests + 5 parity tests (skip until a NEW endpoint exists); real CLI + real HTTP against real servers (legacy in-process from PyPI, or any URL). Verified 4 Oct: 5/5 invariants green on legacy in-process; legacy-vs-live differs only by the edge 403→404 rule (pack Q11) |
| Static-vault conformance | `tests/unit/vault_conformance/test_static_vault_read_path.py` | 5 tests (leak guard now covers `programme/` too); real static file server (stdlib) + real `sgit` CLI + real `sgit_ai` crypto — no mocks |

### The deploy.sgit.ai vault (conformance target + SGit API docs + sgit deploy section)

| Item | Location / value | Notes |
|---|---|---|
| Vault working tree | `vault/` — 26 files: deploy hub + 7 targets + 2 runbooks + scripts + 3 reference (republished 18 Aug from `fyofmkvr` @ `obj-cas-imm-000f0325258c`), `docs/*.md` × 5 (incl. `status.md`, the live refactoring status), sectioned `content.json`, branded docs app | Plaintext — committed deliberately (published vault). Per Dinis (18 Aug): this repo/site IS the deploy section |
| Static site source | `pages/` (`index.html`, `reader.js`, `llms.txt`) | deploy.sgit.ai shell in sgit.ai's light branding: sectioned live viewer + in-browser vault reader (WebCrypto/Node, mirrors `Vault__Crypto`) — no pytest coverage, verified manually in Node |
| Live projection | https://sgit-ai.github.io/SGit-AI__API/ — target hostname **deploy.sgit.ai** (DNS + Pages custom domain pending, human action) | Docs decrypted and rendered in-browser from this same origin |
| Encrypted object store | `vault/.sg_vault/bare/` | Ciphertext mirror, committed (side-by-side pattern) |
| Credential tier | `vault/.sg_vault/local/` | **git-ignored — never committed**; write key escrowed out-of-band |
| Vault ID | `ivpijuvg` | |
| Read key (published) | `c28b118c…0ab817` (full value in `vault/README.md` context, workflow, tests) | Read-only capability; publication is deliberate and permanent |
| **Programme vault** (state + flows of the vaults.sgit.ai programme: `programme.json`, Email-FS lite `mail/`, Issues-FS lite `issues/`, dashboard app) | `programme/` — plaintext mirror only; the vault (id `796sadv6`) is **private**: `.sg_vault/` git-ignored, no read key published, no Pages projection; lives on dev.send.sgraph.ai | Pushed 30 Sep; dashboard verified in headless Chromium against a filesystem-backed `sg.vfs` shim, not yet in the vault web |
| Pages deploy workflow | `.github/workflows/deploy-vault-pages.yml` | Projects `bare/` to `api/vault/read/ivpijuvg/bare/…` on GitHub Pages; needs one-time Pages enablement (Source: GitHub Actions) if `configure-pages` cannot enable it |

Code-verified conformance findings (2026-08-17, sgit-ai v0.15.0):
- Every committed vault object is fetchable byte-identical by plain GET at the live-API path shape — the static read claim **holds** at the storage layer.
- The named-ref filename derives from the read key alone (`Vault__Crypto.derive_ref_file_id`) — no listing/discovery call exists.
- **Gap (pinned by test):** `sgit clone` depends on `POST /api/vault/batch/…` and fails against a static host; the browser transport's `SG_STATIC` fan-out has no CLI equivalent yet.
- A never-pushed vault's named ref points at the empty init commit — `sgit push` (to any SG/Send server, including a local in-memory one) is what forwards it. The committed `bare/` mirror is byte-parity with the server after push.

### CI

| Item | Location | Notes |
|---|---|---|
| **AWS Lambda deploy lane** (dev / main / prod) | `.github/workflows/deploy-aws-lambda.yml` (+ `deploy-aws__{dev,main,prod}.yml`), `deploy/docker/{Dockerfile,serve.py}`, `deploy/aws/{lambda,github-oidc-role}.cfn.yml`, `deploy/aws/cloudfront_ensure_enabled.sh`, `tests/deploy/` | OIDC only; skips deploy until `AWS_DEPLOY_ROLE_ARN` is set. Image = API-only, serving the vault API from the pinned origin package until `sgit_vaults` exists. **Verified 4 Oct locally:** entrypoint boots, smoke 6/6 (3 UI tests skipped by design), parity gate 10/10 vs in-process; cfn-lint clean. **Never run against AWS yet** |
| Base pipeline | `.github/workflows/ci-pipeline.yml` | `workflow_call`: run-tests → increment-tag; uses `owasp-sbot/OSBot-GitHub-Actions` actions |
| Dev pipeline | `.github/workflows/ci-pipeline__dev.yml` | push to `dev` → tests + **minor** tag bump |
| Main pipeline | `.github/workflows/ci-pipeline__main.yml` | push to `main` → tests + **major** tag bump |

Auto-tagging mechanics: the `git__increment-tag` action reads the latest git tag, bumps it,
updates the README release badge + `sgit_ai_api/version` + `pyproject.toml`, commits
("Update release badge and version file") and pushes the new tag. **It requires at least one
existing tag** — the repo is seeded with `v0.1.0`.

### Docs

| Item | Location |
|---|---|
| Extraction dev pack (00–05) | `library/dev_packs/v0.33.59__sgit-api-extraction/` |
| **vaults.sgit.ai dev pack (00–05 + evolution map)** — supersedes the extraction pack's discipline; PROPOSED, nothing implemented | `library/dev_packs/v0.1.5__vaults-sgit-ai/` |
| Architect review of the SG/API across both repos (30 Sep) | `team/roles/architect/reviews/09/30/` |
| Memo response: the Villager transformation (30 Sep) | `team/humans/dinis_cruz/claude-code-web/09/30/` |
| Agent guidance | `.claude/CLAUDE.md` |

---

## DOES NOT EXIST (Commonly Confused)

| Claimed / expected | Reality |
|---|---|
| Any API endpoint (`/api/vault/*`, `/api/transfers/*`, `/api/info/*`, `/mcp`) | PROPOSED — the extraction from `SGraph-AI__App__Send` has not happened yet |
| FastAPI app / Lambda handler / deploy scripts | PROPOSED — arrive with the extraction |
| Deployment jobs in CI (Lambda, container, multi-region) | Lambda lane EXISTS (above), unproven live; container targets / multi-region PROPOSED |
| PyPI / Docker Hub publishing | PROPOSED |

The live SGit API today is still served by the User Lambda deployed from
`SGraph-AI__App__Send`. This repository takes over only after the dev pack's steps 0–5
complete (identical-output test + README test passing).
