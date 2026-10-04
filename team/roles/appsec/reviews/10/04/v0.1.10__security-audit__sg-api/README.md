# v0.1.10 — Security audit of the SG/API refactoring (4 Oct 2026)

Two scoped runs of the vendored Cloudflare `security-audit` skill (`.claude/skills/security-audit/`, pinned `c1c8a8c`). Each run's folder holds the skill's standard outputs: `REPORT.md` (start here), `NEEDS-VALIDATION.md`, `FINDINGS-DETAIL.md`, `architecture.md`, plus machine-readable `findings.json` / `coverage-ledger.json` / `run-metadata.json`. Both pass the skill's validators (`node .claude/skills/security-audit/validate-findings.cjs …`, `validate-coverage-ledger.cjs …`). Keep these files: the skill's next run on the same repo reads them as prior-run input, so coverage builds up across runs.

| Run | Target | Profile | Confirmed | Needs validation | Rejected | Deferred units |
|---|---|---|---|---|---|---|
| [`sgit-ai-api__run-1`](sgit-ai-api__run-1/REPORT.md) | This repo's deploy lane: `deploy/`, `.github/workflows/`, `tests/regression/`, `tests/deploy/` @ `e5f39f6` | quick | **1 high** | 3 | 0 | 2 |
| [`sgraph-ai-app-send__run-1`](sgraph-ai-app-send__run-1/REPORT.md) | The extraction set (`lambda__user/`, `utils/`, `_for_osbot_aws/`) in SGraph-AI__App__Send @ `5d50ae83`, the baseline that the parity gate and deploy lane pin | standard | 0 | 12 | 1 | 1 |

## Act on first

1. **(Confirmed, high) The deploy role can make itself AWS account admin.** `deploy/aws/github-oidc-role.cfn.yml:98-103` grants IAM writes on `role/sgit-vaults-*`, and the role's own name `sgit-vaults-github-deploy` matches that pattern. There is no condition and no permissions boundary. Any job in the `dev` Environment can escalate. Fix before running the bootstrap stack in any shared account. The patch is in `sgit-ai-api__run-1/FINDINGS-DETAIL.md`.
2. **The deploy lane's three leads.** Each needs only an owner to look at GitHub Settings → Environments/Secrets:
   - One role serves all stages, so a dev job holds prod authority.
   - The prod `workflow_dispatch` inputs can inject shell commands into the credentialed deploy step.
   - Following the README can leave prod with the access-token check disabled while the pipeline stays green.
3. **SG/API leads to settle before the code moves here.** They move with the code, so fix them in the move or right after it:
   - The presigned download-url skips expiry and download limits.
   - The presigned upload-url lets any token holder overwrite or resurrect transfers.
   - The vault `file_id` is never validated (`..` escape on disk storage, which `deploy/aws/ec2.cfn.yml` in the origin repo defaults to).
   - The append and manifest caches go stale after a vault is destroyed.

## Method and limits (read before quoting any result)

- **Source-only.** The origin package's runtime deps are not installed, and the skill forbids fetching them, so no target code ran. That is why Run A has zero confirmed records. Each lead names the exact library or deployment fact that blocks it, a bounded local plan, and an owner-observed check. None of these checks needs traffic against a deployment.
- **Deviations from the skill, for transparency:**
  - Run B used 2 recon agents instead of 4, because the target is about 1.5k lines.
  - Run A grouped related candidates per verifier to fit a 30-agent budget. Verifiers stayed independent of hunters, and Phase 3 and Phase 5 always used different agents.
  - Run A ran its Phase 3 verifiers in parallel with the wave-2 hunter, because they had no dependency on it.
- **Coverage is partial and stated as such.** Deferred units:
  - Run B: deploy lifecycle modes (bootstrap-stack self-update, rollback, teardown); the GitHub Pages projection.
  - Run A: the `X-Vault-Public` public-bucket lane.
  - No final-clean critic ran in either run.
- No live endpoints, AWS, or GitHub APIs were touched. The one shell fixture (the quote breakout in the deploy workflow) used a dummy marker under `unshare -rn env -i timeout prlimit`.

## Disclosure note

This repository is public. Run B's findings concern this repo's own unmerged deploy lane, which has never run against AWS. Run A's leads concern code in another public repository, already discussed in that repo's own AppSec reviews. None of them is a confirmed exploitable vulnerability. If a lead is confirmed later, record the fix status here.
