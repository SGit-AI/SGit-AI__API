# Roadmap — from this vault to a deployable API

The objective: everything described on [sgit.ai/deploy](https://sgit.ai/deploy/index.html)
— Docker, AWS, GCP, Heroku, static — working and deployed **from this repository**, so
that someone who has never seen the code can deploy the SGit API following only the
README (the "README test"). Where things stand and what is next, in order:

## Done (verified)

1. **CI pipeline live** — tests + auto-tagging on `dev`/`main` (bootstrap, 17 Aug).
2. **Reference vault + static projection** — this vault, committed to git, deployed to
   GitHub Pages at live-API paths, read entirely by GETs.
3. **Conformance suite in CI** — the static read claim is now enforced on every push,
   and the CLI's batch gap is pinned as a good-failure test.
4. **Hermetic server rehearsal** — the current PyPI build of the origin service boots
   locally in memory mode (`SEND__STORAGE_MODE=MEMORY`) and accepts a real `sgit push`;
   this is how this vault's named branch is forwarded without touching production.

## Next (in order)

5. **The extraction** (the dev pack's steps 0–5): move the User Lambda's reachable set
   from `SGraph-AI__App__Send` into `sgit_ai_api/`, zero changes, verified by the
   identical-output test (Lambda zip member hashes) and the same test counts
   (512 passed / 9 skipped baseline). Gated on a go-ahead brief.
6. **Serve the API from this repo in CI** — boot the extracted service in-memory inside
   the test suite (replacing the PyPI package in the vault-publish rehearsal), then add
   the deploy jobs: Lambda first (identical output), then container targets.
7. **The deployment matrix** — the sgit.ai/deploy guidance made executable: one deploy
   job per platform, each ending in the same conformance check against the deployed
   endpoint (`/api/info/*` + the read contract).
8. **Static clone in the CLI** (proposal filed with the CLI team) — flips this repo's
   pinned good-failure test into a full clone-from-Pages check, closing the loop:
   publish on release, clone statically in CI, fail the build on drift.
9. **The deploy docs vault** — the vault behind sgit.ai/deploy, maintained where the
   deployment code lives (thread open on where it should be hosted; this repo is the
   candidate, since the README test and the deploy docs are the same artefact).

## The invariant across all of it

The API contract (`/api/vault/*`, `/api/transfers/*`, `/api/presigned/*`, `/api/info/*`,
`/mcp`; the auth headers) does not change — during the move or after it. The conformance
suite and, once generated, the published GET-only `openapi.json` are the executable form
of that promise.
