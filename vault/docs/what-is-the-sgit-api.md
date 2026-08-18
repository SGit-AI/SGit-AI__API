# What is the SGit API

The SGit API is the **server side of the sgit protocol**: the deployable service that the
`sgit` CLI (PyPI: `sgit-ai`), the SG/Vault web UI, and vault apps all talk to. It has one
job, and the job is deliberately small: **store ciphertext under opaque ids, and give it
back**.

Everything interesting happens in the client. Files are encrypted with AES-256-GCM before
they leave your machine; filenames, commit messages and directory structure are encrypted
metadata; object names are content hashes or HMACs computed from a key the server never
sees. What reaches the API is bytes under meaningless names.

## What the server can and cannot see

| The server sees | The server never sees |
|---|---|
| the vault id | your passphrase or vault key |
| opaque object ids | filenames or directory structure |
| ciphertext blobs and their sizes | file contents |
| request timing | commit messages |

This is not a policy promise — it is structural. There is no code path on the server that
could read a document, because the decryption keys never reach it.

## Where the API lives today, and where it is going

Today the live service is the **User Lambda** deployed from
[`SGraph-AI__App__Send`](https://github.com/the-cyber-boardroom/SGraph-AI__App__Send).
This repository — [`SGit-AI/SGit-AI__API`](https://github.com/SGit-AI/SGit-AI__API) — is
its future home: the extraction brief moves the User Lambda's reachable set here with
zero changes, verified by an identical-output test, so the API can be deployed from this
repo to multiple platforms and regions. Until that lands, this repo holds the CI
pipeline, this documentation vault, and the conformance suite — the reality document in
the repo is the authoritative statement of what exists where.

## The contract that must not change

The API surface consumed by the sgit client and the vault web UI is frozen during and
after the move:

- routes: `/api/vault/*`, `/api/transfers/*`, `/api/presigned/*`, `/api/info/*`, `/mcp`
- auth headers: `x-sgraph-access-token`, `x-sgraph-vault-write-key`, `x-vault-read-key`,
  `x-vault-enum-key`, `x-vault-public`

The read subset of that contract is small enough to serve from a folder — which is what
this vault demonstrates. See **The read contract** and **Static hosting** in this vault's
docs.
