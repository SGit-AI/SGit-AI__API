# 02 — Decisions and Questions (phase 2)

Resolve before anything in `01` is built. Mirrored in the programme vault's `programme.json` (phase 2 steps) and answered by message to `architect.villager`.

## Decisions (Dinis)

| # | Decision | Options | Recommendation | Answer / date |
|---|---|---|---|---|
| P2-D1 | **Sequencing vs phase 1** | (a) strictly after cutover (1.7); (b) in parallel on the new repo from step 1.2, Explorer branch, never merged before 1.7; (c) fold into phase 1 | **(b)** — the new repo exists from 1.2; phase-2 work lands on a branch and mounts beside the phase-1 app; (c) would break the parity proof | |
| P2-D2 | **Which services ship first** | keys / kv / secrets in any order; auth mode 3 alone first | **Auth mode 3 first** (step 2.1: severs the Send Admin dependency, smallest, and proves the "server reads a vault" primitive), then `keys/check`, then secrets, then kv | |
| P2-D3 | **Where the supporting vaults live by default** | same deployment; a dedicated "control" deployment; static host for read-only ones | **Same deployment by default**, with the ids/read keys as configuration so a control deployment is one config change; document both | |
| P2-D4 | **PKI before apps endpoints** | ship `keys/check` behind the access token first, PKI later; or PKI first | **PKI first.** `keys/check` is an existence signal for `H(key)`; only identified principals may see it | |
| P2-D5 | **Rotation cadence and what the weekly job covers** | tokens only; tokens + principals; + deployment keypair; + backups + restore drill | **tokens + backups + restore drill weekly**; principals and deployment keypair monthly; vault keys never (migration only) | |
| P2-D6 | **Telemetry granularity** | per request (rejected: the 22 Feb incident); per (channel, hour); per (channel, day) | **per (channel, hour)**, one append token per channel per day (09/07 design) | |
| P2-D7 | **Pruning routes** | now, by judgement; after N weeks of telemetry | **after 4 weeks of telemetry** on vaults.sgit.ai; until then phase 1's surface is frozen | |
| P2-D8 | **`sgit deploy` vs the ephemeral deploy server** | CLI-first; server-first; both | **CLI-first** (`sgit deploy`), server as the same script behind a Router Lambda afterwards | |

## Questions

| # | Question | Why it matters | Default | Answer / date |
|---|---|---|---|---|
| P2-Q1 | Does a deployment's private key *derive* the read keys of its supporting vaults (one secret, HKDF), or are they *given* to it (secrets vault holds them)? | one-secret bootstrap vs simpler key handling | **given**, via the secrets vault; the deployment key opens the secrets vault only | |
| P2-Q2 | Do tenant vaults on vaults.sgit.ai get their own credentials vault, or share the deployment's? | multi-tenant hosted vs single-tenant self-host | **share by default**; per-tenant when billing arrives | |
| P2-Q3 | Which signature scheme for signed requests: ECDSA P-256 (matches `sgit keygen` + SecureChannel) or Ed25519? | CLI and browser already have P-256 | **P-256** | |
| P2-Q4 | Does `keys/check` return the record ciphertext, or only status? | ciphertext keeps the server blind; status is simpler for callers without the key | **ciphertext**; a status-only variant is a caller-side helper | |
| P2-Q5 | Where does the rotation job run: GitHub Actions cron in the deployment's repo, or a scheduled Lambda in the deployment? | self-host without GitHub | **both documented**; Actions first (it is where the README test lives) | |
| P2-Q6 | CLI team: `sgit deploy`, `sgit keys issue/revoke`, `sgit secrets get/put` (all PROPOSED in the reality doc) — who builds the CLI half? | the services are useless without a client | thread with `cli.sgit` after P2-D2 | |
| P2-Q7 | Is Send's Admin Lambda token store migrated into the first credentials vault (so existing hosted tokens keep working), or do hosted users get new keys? | continuity for existing users at cutover | **migrate once** at 2.1, same as the D5 data copy | |
| P2-Q8 | Does the dashboard for telemetry live in the programme vault, the deploy-docs vault, or a new per-deployment vault app? | where operators look | **per-deployment vault app** (it reads that deployment's telemetry vault) | |

## What the phase-2 steps become once answered

| Step | Deliverable | Gate |
|---|---|---|
| 2.1 | auth mode 3: `Vault__Reader` + `Service__Access_Token` branch; migration of hosted tokens | a hosted vaults.sgit.ai validates tokens with no call to Send |
| 2.2 | PKI: principals registry, signed-request verifier, `sgit` client side | one route accepts only signed requests from an enrolled principal |
| 2.3 | `keys/check` + issue/revoke lanes + operator job | an agent checks its own key and decrypts the record |
| 2.4 | secrets vault + `secrets/<name>`; the deployment boots from one key | `docker run -e VAULTS__DEPLOYMENT_KEY=…` and nothing else |
| 2.5 | telemetry lane + per-deployment dashboard app | per-vault read/write counts visible, no plaintext |
| 2.6 | `sgit deploy` creating the supporting vaults on first boot; rotation + backup + restore drill on a schedule | a new region from one command; a weekly drill passes |
| 2.7 | route pruning from 4 weeks of telemetry | a deletion series with a reason per commit |

*Released under CC BY 4.0.*
