The deployment scripts live in the open in the
[SGraph-AI__App__Send repo](https://github.com/the-cyber-boardroom/SGraph-AI__App__Send)
under `deploy/` — this vault documents them; the repo is their source of truth.

| Artifact | Path in repo | Status |
|---|---|---|
| Lambda stack | `deploy/aws/lambda.cfn.yml` | ✅ written, lint-clean, beta |
| EC2 appliance stack | `deploy/aws/ec2.cfn.yml` | ✅ written, lint-clean, beta |
| Fargate cluster stack | `deploy/aws/ecs-fargate.cfn.yml` | ✅ written, lint-clean, beta |
| AMI bake pipeline | `deploy/aws/ami-pipeline.cfn.yml` | ✅ written, lint-clean, beta |
| GitHub OIDC bootstrap | `deploy/aws/github-oidc-role.cfn.yml` | ✅ written, lint-clean |
| Full-cycle CI pipeline | `.github/workflows/deploy-full-cycle.yml` | ✅ written; first live run pending |
| Shared smoke suite | `tests/deploy/targets/test_smoke__deployed_target.py` | ✅ validated against a live container |
| Terraform modules | `deploy/terraform/modules/*` | 🚧 next up (Phase B2) |
| Heroku button contract | `app.json` + `heroku.yml` (repo root) | ✅ written |

*Beta = code-complete and lint-clean; flips to stable when the full-cycle pipeline is green
against a live account.*
