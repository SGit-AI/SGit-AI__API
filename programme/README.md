# The programme vault — vaults.sgit.ai

This vault **manages and presents** the vaults.sgit.ai programme: the Villager transformation of the
vault platform (phase 1) and the vault services that follow it (phase 2). It does not hold the
substance — the packs, reviews and code live in git — it holds the **state and the flows**: which
step is where, which decisions are open, who is waiting on whom, and the messages between the
agents and the human. `briefs/index.md` points at everything else.

It exists because a programme with a human, seven agent roles, two repos and an external CLI team
has more flows than a brief can carry. A vault is the right memory for that: single-writer paths are
interfaces between agents, every change is a commit, and the dashboard renders the whole thing from
the files.

## What is in it

| Path | Convention | Written by |
|---|---|---|
| `programme.json` | the structured state: phases → steps (status, owner, gate), decisions D1–D10, questions Q1–Q10, the agent roster | `architect.villager` only — ask by message |
| `mail/` | **Email-FS lite** (`__Send` brief 05/06): `mail/<agent>/{inbox,done,outbox/<recipient>}`; `mail/mailroom/<recipient>/` is the only shared zone | each agent under its own name; anyone may drop a file in a mailroom |
| `issues/` | **Issues-FS lite** (same brief, §7): `issues/<agent>/{open,blocked,done}/NNN-slug.md` with `created`, `priority`, optional `blocked_on` | each agent under its own name |
| `briefs/index.md` | pointers into git | `librarian.villager` |
| `index.html` + `.vault/app.json` | the dashboard app: reads all of the above over `sg.vfs`, writes only into `mail/mailroom/` | `architect.villager` |

Agent names are `{role}.{team}`: `dinis.human`, `architect.villager`, `dev.villager`, `devops.villager`,
`qa.villager`, `cartographer.villager`, `librarian.villager`, `cli.sgit`, `explorer.send`.

## The rules (lite, unchanged)

1. **Single writer.** You write only under `mail/<you>/` and `issues/<you>/`, plus *new* files in
   `mail/mailroom/<recipient>/`. You may read anyone's issues; to change them, send a message.
2. **Send / deliver / done.** SEND = write to `mail/mailroom/<r>/NNN-slug.eml` and copy to your
   `outbox/<r>/`. DELIVER = the recipient moves it into their `inbox/`. DONE = they move it to
   `done/` when the work is done, not when they replied. A file still in the mailroom = not yet read.
3. **Messages are `.eml`** (RFC 2822 headers, Markdown body) with `X-EmailFS-Kind`
   (`task|reply|notification|question|handoff|debrief`) and `X-EmailFS-Priority`. Replies carry
   `In-Reply-To` / `References`. Numbering is per sender→recipient pair.
4. **One commit per cycle**: pull → deliver → work → send → done → `sgit commit "<you> check-in: …"`
   → `sgit push`. `sgit pull`'s diff is your notification.
5. **Decisions and questions** are answered by message to `architect.villager` (or the dashboard's
   Answer form, which writes the same file). The architect updates `programme.json` and the pack's
   `05__open-questions.md` from the reply — the git file stays the record, this vault stays the view.

## How it is published

**This vault is private.** Unlike the deploy vault, neither its ciphertext nor a read key is in
the repository: the whole `.sg_vault/` tree is git-ignored, and the vault lives on the live
SG/Send server, opened with the vault key held by the programme's participants (escrowed with
Dinis; shared out-of-band, never committed). What *is* in git is this plaintext working tree —
the human-readable mirror, kept in step by the same `sgit commit` + `git commit` cycle.

- Vault id: `796sadv6` (an id is not a credential)
- Open: `dev.vault.sgraph.ai/#<vault-key>` — or `sgit clone <vault-key> --base-url https://dev.send.sgraph.ai --token <access-token>`
- Static projection: none, by design.

## Why not just the pack files

Because the pack is a plan and this is a runtime. The pack says what should happen; this vault says
what *is* happening, who has the ball, and what was said to whom. When phase 1 lands and phase 2
starts, the same vault carries on — the packs are versioned folders, the programme is one vault.
