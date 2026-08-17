# Reality Document — SGit-AI__API

**Code-verified record of what exists in this repository.**
Rule: if it is not listed here, it does not exist. Anything described elsewhere that is not
here must be labelled "PROPOSED — does not exist yet."

**Last verified:** 2026-08-17 (repo bootstrap)

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
