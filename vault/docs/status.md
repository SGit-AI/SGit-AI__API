# The refactoring, live

The SGit API is being extracted from
[SGraph-AI__App__Send](https://github.com/the-cyber-boardroom/SGraph-AI__App__Send) (the
User Lambda's reachable set) into
[SGit-AI/SGit-AI__API](https://github.com/SGit-AI/SGit-AI__API) — the repository this
vault lives in. This page is the running status of that move. It is updated by `sgit
push` in the same commits as the work itself; if it disagrees with the repo's reality
document, the reality document wins.

**Last updated:** 2026-08-18

## Where things stand

| Milestone | Status | Evidence |
|---|---|---|
| Repo bootstrap: CI pipeline (tests → auto-tag) on dev/main | ✅ 17 Aug | tags v0.1.0 → v0.1.3+, every dev push tested and tagged |
| Reference vault, committed encrypted store, GitHub Pages projection | ✅ 17 Aug | this vault; the page you are probably reading |
| Static-read conformance suite in CI | ✅ 17 Aug | tests/unit/vault_conformance — 5 tests on every push |
| In-browser static reader (WebCrypto, mirrors Vault__Crypto) | ✅ 18 Aug | pages/reader.js — it decrypted this page |
| Deploy docs republished from the SG/Send team's vault | ✅ 18 Aug | this vault, from fyofmkvr @ obj-cas-imm-000f0325258c |
| Static-clone proposal filed with the sgit CLI team | ✅ 17 Aug | team/comms/briefs/08/17 — architecture round pending |
| The extraction itself (User Lambda reachable set → sgit_ai_api/) | 🚧 next | gated on a go-ahead brief; dev pack steps 0–5 |
| API served from this repo in CI (in-memory, no mocks) | 🚧 planned | rehearsed 17 Aug with the PyPI build of the origin service |
| Deploy jobs (Lambda identical-output, then container targets) | 🚧 planned | the deployment matrix — one job per target in this vault's guides |
| sgit.ai/deploy pointed at this vault | 🚧 pending handover | thread open in team/comms/briefs |

## The verification discipline

- **Move with zero changes**; prove it with the identical-output test (Lambda zip member
  hashes) and identical test counts (origin baseline: 512 passed / 9 skipped).
- **The reality document** (`team/roles/librarian/reality/`) is the code-verified record
  — nothing is claimed shipped unless it is listed there.
- **The conformance loop**: this vault is published statically on every merge, and CI
  reads it back with no server. Anything that breaks against a static host is a hidden
  server dependency, caught before it ships.

## Known gaps, stated plainly

- `sgit clone` cannot yet read from the static host (batch-endpoint dependency) — pinned
  by a good-failure test; proposal filed.
- This vault has not yet been pushed to a production SG/Send server; the git repository
  and the static projection are the authoritative copies.
- The deploy guides below still reference the origin repo's artifacts until the
  extraction lands here.
