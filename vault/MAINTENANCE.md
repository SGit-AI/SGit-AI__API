# How This Vault Is Maintained

This vault is the public documentation home for deploying sgit's server side (SG/Send —
the SGit API). As of 18 Aug 2026 it lives in the
[SGit-AI/SGit-AI__API](https://github.com/SGit-AI/SGit-AI__API) repository — the repo the
API itself will deploy from — republished from the SG/Send team's original deploy vault
(`fyofmkvr`, commit `obj-cas-imm-000f0325258c`), which remains the live source for
sgit.ai/deploy until the handover is completed there.

The workflow:

1. Deployment code changes land in `SGit-AI/SGit-AI__API` (and, until the extraction
   completes, in the origin repo
   [SGraph-AI__App__Send](https://github.com/the-cyber-boardroom/SGraph-AI__App__Send)).
2. The matching guidance pages here are updated **in the same commit** — the vault's
   working tree is plaintext in the repo, so docs review happens in the pull request.
3. `sgit commit` + `sgit push` forwards the vault's named branch (write access = vault
   key holders only; the key is escrowed, never committed).
4. The repo's Pages workflow projects the encrypted store to the static site
   (deploy.sgit.ai / sgit-ai.github.io/SGit-AI__API) — where these pages are decrypted
   and rendered in the reader's browser.

Status legend used throughout: ✅ works today, exactly as written · 🚧 in progress — the
page says precisely what exists and what is coming. Honesty rule: nothing is described as
shipped unless it is code-verified in the repo's reality documents
(`team/roles/librarian/reality/`).
