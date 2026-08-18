# Reality Document — SGit-AI__API

**Code-verified record of what exists in this repository.**
Rule: if it is not listed here, it does not exist. Anything described elsewhere that is not
here must be labelled "PROPOSED — does not exist yet."

**Last verified:** 2026-08-17 (repo bootstrap + CI verified live + reference vault added)

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
| Static-vault conformance | `tests/unit/vault_conformance/test_static_vault_read_path.py` | 5 tests; real static file server (stdlib) + real `sgit` CLI + real `sgit_ai` crypto — no mocks |

### Reference vault (static-deployment conformance target + SGit API docs vault)

| Item | Location / value | Notes |
|---|---|---|
| Vault working tree | `vault/` (README, `content.json`, `docs/*.md` × 4, `index.html` docs app, `app.json`) | Plaintext — committed deliberately (published vault); since 17 Aug also the API's documentation |
| Static site source | `pages/` (`index.html`, `reader.js`, `llms.txt`) | The GitHub Pages shell: publishing page + in-browser vault reader (WebCrypto/Node, mirrors `Vault__Crypto`) — no pytest coverage, verified manually in Node |
| Live projection | https://sgit-ai.github.io/SGit-AI__API/ | Docs decrypted and rendered in-browser from this same origin |
| Encrypted object store | `vault/.sg_vault/bare/` | Ciphertext mirror, committed (side-by-side pattern) |
| Credential tier | `vault/.sg_vault/local/` | **git-ignored — never committed**; write key escrowed out-of-band |
| Vault ID | `ivpijuvg` | |
| Read key (published) | `c28b118c…0ab817` (full value in `vault/README.md` context, workflow, tests) | Read-only capability; publication is deliberate and permanent |
| Pages deploy workflow | `.github/workflows/deploy-vault-pages.yml` | Projects `bare/` to `api/vault/read/ivpijuvg/bare/…` on GitHub Pages; needs one-time Pages enablement (Source: GitHub Actions) if `configure-pages` cannot enable it |

Code-verified conformance findings (2026-08-17, sgit-ai v0.15.0):
- Every committed vault object is fetchable byte-identical by plain GET at the live-API path shape — the static read claim **holds** at the storage layer.
- The named-ref filename derives from the read key alone (`Vault__Crypto.derive_ref_file_id`) — no listing/discovery call exists.
- **Gap (pinned by test):** `sgit clone` depends on `POST /api/vault/batch/…` and fails against a static host; the browser transport's `SG_STATIC` fan-out has no CLI equivalent yet.
- A never-pushed vault's named ref points at the empty init commit — `sgit push` (to any SG/Send server, including a local in-memory one) is what forwards it. The committed `bare/` mirror is byte-parity with the server after push.

### CI

| Item | Location | Notes |
|---|---|---|
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
| Agent guidance | `.claude/CLAUDE.md` |

---

## DOES NOT EXIST (Commonly Confused)

| Claimed / expected | Reality |
|---|---|
| Any API endpoint (`/api/vault/*`, `/api/transfers/*`, `/api/info/*`, `/mcp`) | PROPOSED — the extraction from `SGraph-AI__App__Send` has not happened yet |
| FastAPI app / Lambda handler / deploy scripts | PROPOSED — arrive with the extraction |
| Deployment jobs in CI (Lambda, container, multi-region) | PROPOSED — CI currently only tests and tags |
| PyPI / Docker Hub publishing | PROPOSED |

The live SGit API today is still served by the User Lambda deployed from
`SGraph-AI__App__Send`. This repository takes over only after the dev pack's steps 0–5
complete (identical-output test + README test passing).
