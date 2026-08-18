# SGit API — Reference Vault

This is the **reference vault** for the SGit API (`SGit-AI/SGit-AI__API`): a small, stable,
representative encrypted vault whose job is to be a **conformance target**, per the
16 August 2026 dev brief *"A vault on a static host is a conformance test"*.

The product's central claim is that the server is storage which reads nothing: every read
is a GET of a path computed from a key, and decryption happens in the client. A pure
static host (GitHub Pages) is the strongest available proof of that claim — anything that
stops working there is a hidden dependency on server behaviour.

Since 17 Aug it is also the **documentation vault of the SGit API**: the docs are written
here, served from ciphertext, and rendered wherever the vault lands — the official vault
UI, the GitHub Pages projection, or a git checkout.

## What this vault contains

| File | Purpose |
|---|---|
| `README.md` | This document |
| `content.json` | The conformance claims + docs navigation, read by the app over the `sg.vfs` bridge |
| `docs/what-is-the-sgit-api.md` | What the API is, what the server can/cannot see, where the code lives |
| `docs/read-contract.md` | The GET walk, the client-side derivations, the cache semantics |
| `docs/static-hosting.md` | This deployment: the conformance framing and the three things that break |
| `docs/roadmap.md` | Done / next, in order, toward the sgit.ai/deploy objective |
| `index.html` | A self-contained docs app: nav + markdown rendering, CSS/JS inlined per the authoring contract |
| `app.json` | App manifest — `index.html` auto-opens when the vault is opened |

## How it is published

- The vault's encrypted object store (`.sg_vault/bare/`) is committed to this git
  repository (side-by-side pattern; `.sg_vault/local/` — the write credential tier —
  is git-ignored and must never be committed).
- A GitHub Actions workflow projects that tree to GitHub Pages under
  `api/vault/read/<vault-id>/bare/…` — the exact paths the live API serves — so any
  client that can read from the API can read from the static host.
- The read key is published deliberately. It grants read, and only read; the write key
  is escrowed out-of-band and never enters this repository.

## The three things that break on a static host

1. **Batch reads** — a POST carrying a list; a static host serves files. (The real
   problem; the CLI's clone currently depends on it.)
2. **All writes** — nothing accepts them. Intended: this is a published read-only snapshot.
3. **Authentication and rate limiting** — no server to enforce either. Acceptable:
   the content is ciphertext and the read key is published by design.

The unit test suite in this repository pins all three, so a change in any of them is a
loud, classified failure rather than a silent drift.
