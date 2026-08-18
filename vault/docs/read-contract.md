# The read contract

Reading a vault is a sequence of GETs of paths the client computes. No listing, no query,
no server logic — which is why the read contract can be served by the live API and by a
plain static host interchangeably.

## The walk

```
read key ─┬─ HMAC ─▶ ref file id            (computed, no request)
          │
          ▼
GET  /api/vault/read/<vault-id>/bare/refs/<ref-id>        → the current commit id
GET  /api/vault/read/<vault-id>/bare/data/<commit-id>     → the commit (tree id, parents)
GET  /api/vault/read/<vault-id>/bare/data/<tree-id>       → the tree (entries, names enc)
GET  /api/vault/read/<vault-id>/bare/data/<blob-id>       → a file's ciphertext
          │
          ▼
decrypt locally (AES-256-GCM, iv‖ciphertext; names/sizes are encrypted metadata)
```

## Derivations (all client-side)

| Value | Derivation |
|---|---|
| ref file id | `'ref-pid-muw-' + hex(HMAC-SHA256(read_key, 'sg-vault-v1:file-id:ref:' + vault_id))[:12]` |
| branch index id | same, domain `'sg-vault-v1:file-id:branch-index'` |
| object ids | `'obj-cas-imm-' + sha256(ciphertext)[:12]` — content-addressed |
| read key | one-way from the vault key (PBKDF2-HMAC-SHA256, 600k iterations) — publishable, cannot become write access |

## Cache semantics fall out of the naming

- `*-imm-*` objects are content-addressed and **immutable**: cache forever, they can
  never be stale.
- `ref-pid-muw-*` is the one **mutable** pointer: it is the only thing a reader ever has
  to re-check. Everything a page after the first load costs is one small GET of the ref.

## What is NOT in the read contract

Batch reads (`POST /api/vault/batch/<id>`), all writes, and all authentication. Batch is
an optimisation the live API offers; writes and auth are the live API's other half. None
of them are needed to read — the conformance suite in this repository pins exactly that
boundary, and the one place today's CLI still crosses it (clone's batch dependency) is
tracked by a good-failure test and a proposal brief to the CLI team.
