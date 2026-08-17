# Team — SGit-AI__API

This folder mirrors the team structure of
[`SGraph-AI__App__Send`](https://github.com/the-cyber-boardroom/SGraph-AI__App__Send)
(see that repo's `.claude/CLAUDE.md` for the full role system: 18 roles across the
Explorer / Villager / Town Planner teams).

| Folder | Purpose | Writable by |
|---|---|---|
| `roles/{role}/reviews/MM/DD/` | Role review documents | Agents (in role) |
| `roles/librarian/reality/` | Code-verified reality document | Librarian (same commit as code changes) |
| `comms/` | Agent-to-agent communication (changelog, QA briefs) | Agents |
| `humans/dinis_cruz/briefs/` | Human briefs — **READ-ONLY for agents, no exceptions** | Human only |
| `humans/dinis_cruz/debriefs/MM/DD/` | Human-facing session summaries | Agents |
| `humans/dinis_cruz/claude-code-web/MM/DD/` | Agent session outputs (decisions, observations) | Agents |
