# Static hosting — this deployment

The page you are (probably) reading this on is a **pure static projection** of this
vault: the encrypted object store, committed to the repo and served by GitHub Pages at
the exact paths the live API serves. There is no server. The browser derived the ref
filename from the published read key, fetched ciphertext with plain GETs from the same
origin, and decrypted everything locally with the Web Crypto API.

## Why this exists: a conformance test, not a demo

The product's central claim is that the server is storage which reads nothing. A static
host is the strongest available proof: it cannot query, compute, authenticate or be
configured. Anything that stops working here is a hidden dependency on server behaviour.
So this deployment is wired into continuous integration — the repo's test suite serves
the committed store from a real static file server and verifies the read path on every
push.

## Exactly three things break here

| Breaks | Why | Verdict |
|---|---|---|
| Batch reads | a POST carrying a list; static hosts serve files | the one real gap — the CLI's clone still uses it; proposal filed |
| All writes | nothing accepts them | intended: this is a published read-only snapshot |
| Auth and rate limiting | no server to enforce them | intended: the read key is published, the ciphertext is the protection |

## The shape of the deployment

- **A projection, not a mirror.** Only the objects reachable from the current head are
  published. Encrypted objects neither compress nor delta, hosts cap site size, and
  history grows forever — so the static copy is regenerated per publish and is *not* a
  backup. The git repository is the mirror with history.
- **Same origin for vault and page.** GitHub Pages permits no custom response headers,
  so the reader and the ciphertext share an origin and the CORS question never arises.
- **The read key is in the open, on purpose.** It grants read, and only read; it cannot
  be turned into write access; and its publication is permanent — a key committed to a
  repository is in the history forever, which is the same decision as publishing it.

## Reproduce it

```
# from the repo checkout — no network needed:
python3 -m http.server --directory <assembled-site>   # or just run the test suite
pytest tests/unit/vault_conformance/

# from anywhere:
GET https://sgit-ai.github.io/SGit-AI__API/api/vault/read/ivpijuvg/bare/refs/<derived-ref-id>
```
