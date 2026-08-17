# SGit-AI__API

![release](https://img.shields.io/badge/release-v0.1.3-blue)

**The server side of the sgit protocol** — the deployable API service consumed by the
[`sgit` CLI](https://github.com/SGit-AI/SGit-AI__CLI) (PyPI: `sgit-ai`) and the vault web UI.
Zero-knowledge by design: the server stores ciphertext only; encryption keys never leave the
client.

## Status

**Scaffolding + CI only.** The API code is being extracted from
[`SGraph-AI__App__Send`](https://github.com/the-cyber-boardroom/SGraph-AI__App__Send)
(the User Lambda's reachable set). The extraction brief pack — scope, ADRs, implementation
plan, and acceptance criteria — is in
[`library/dev_packs/v0.33.59__sgit-api-extraction/`](library/dev_packs/v0.33.59__sgit-api-extraction/00__README.md).

Until that completes, the live API is still deployed from the origin repo.

## Development

```bash
pip install -r requirements-test.txt
python -m pytest tests/unit -q
```

## CI

| Trigger | Pipeline | What it does |
|---|---|---|
| push to `dev` | `ci-pipeline__dev.yml` | unit tests → **minor** tag bump (`vX.Y.Z+1`) |
| push to `main` | `ci-pipeline__main.yml` | unit tests → **major** tag bump (`vX.Y+1.0`) |

Both call the shared `ci-pipeline.yml` (`workflow_call`). Tagging updates the badge above,
`sgit_ai_api/version`, and `pyproject.toml` automatically — **never edit those by hand.**

## Working agreements

Agents and contributors: read [`.claude/CLAUDE.md`](.claude/CLAUDE.md) first. The
code-verified record of what exists is
[`team/roles/librarian/reality/index.md`](team/roles/librarian/reality/index.md).
