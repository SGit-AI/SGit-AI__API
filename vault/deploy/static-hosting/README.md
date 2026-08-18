[🏠 Deploy Hub](../../00-START-HERE.md) › **Static hosting**

# Publish a Vault to a Static Host (no server)

A vault can be published as **plain static files**: the vault UI + a mirror of the encrypted
object tree. Any static host then serves a **read-only vault** — the browser fetches
ciphertext and decrypts locally. GitHub Pages, S3+CloudFront, Netlify, Cloudflare Pages,
GCS+Firebase, even a Heroku static buildpack.

**What exists today:** the vault client's static mode (`SGSend.staticMode`) and read-only
share tokens. **In progress:** the one-command exporter (`sgit publish-static`) and
per-target publish recipes.

Two access models:
- **Public projection** — the read-only token is published with the site: anyone with the URL can read.
- **Locked projection** — files only; the token travels out-of-band: URL is public, content is not.

The write key is never published, in either model. Full details live in the repo brief:
`team/comms/briefs/08/11/v0.33.54__technical-brief__static-vault-hosting.md`.
