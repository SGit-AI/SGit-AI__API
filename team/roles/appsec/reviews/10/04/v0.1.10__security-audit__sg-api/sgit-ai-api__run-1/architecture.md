# Architecture — SGit-AI__API deploy lane (quick, scoped)

**Product/principals.** SGit-AI__API is receiving the extracted SG/API (sgit encrypted-vault server). Today its code-bearing surface is a deploy lane that builds an API-only container from the pinned origin package (SGraph-AI__App__Send @ 5d50ae83) and deploys it to AWS Lambda per stage (dev/main/prod) via GitHub OIDC. Principals: repo writers/dispatchers (can push branches, run workflow_dispatch), PR authors (same-repo and fork), GitHub-hosted runners, the OIDC deploy role `sgit-vaults-github-deploy`, the Lambda execution role `sgit-vaults-lambda--{stage}`, anonymous internet callers of the deployed Function URL / CloudFront, and the operator who sets GitHub secrets/environments. Protected resources: the AWS account (IAM, Route53, CloudFront), stage buckets of ciphertext vault data, the per-stage API access token, GitHub write token, release tags.

**Stack.** GitHub Actions (reusable `workflow_call` pipelines), CloudFormation (`deploy/aws/*.cfn.yml`), Docker image (python:3.12-slim + AWS Lambda Web Adapter 0.9.1, tag-pinned), uvicorn `deploy/docker/serve.py`, pytest smoke/parity suites driving the real `sgit` CLI. No local cfn-lint/aws CLI; source-only review.

**Entry surfaces / paths.**
- Workflow triggers: push dev/main, workflow_dispatch (prod: free-text `domain_name`, `hosted_zone_id`, `certificate_arn`; parity: free-text `new_url`), pull_request (regression-parity.yml), workflow_call inputs → `run:` shell at `.github/workflows/deploy-aws-lambda.yml:69,126-136,189,199-202`.
- Secrets: `AWS_DEPLOY_ROLE_ARN`, `SGIT_VAULTS__ACCESS_TOKEN__{DEV,MAIN,PROD}` → reusable `ACCESS_TOKEN` → CFN `AccessToken` (NoEcho) → Lambda env `SGRAPH_SEND__ACCESS_TOKEN` (`deploy/aws/lambda.cfn.yml:45,140`); `SG_NEW_TOKEN` → regression tests (`regression-parity.yml:45-46`) → `sgit --token` argv (`tests/regression/sgit_scenarios.py:55-57`).
- Build inputs: GitHub archive tarball of origin commit (no hash), unpinned pip deps, tag-pinned base images, `owasp-sbot/OSBot-GitHub-Actions@dev` (mutable) in `ci-pipeline.yml:33,46` (contents: write) and `deploy-aws-lambda.yml:57` (workflow-level id-token: write).
- Deployed service: Function URL AuthType NONE + Principal '*' (`lambda.cfn.yml:146-155`), optional CloudFront forwarding all viewer headers; app auth = env token (empty → open instance with a warning only, `deploy-aws-lambda.yml:131`).

**Trust boundaries & strongest visible control.**
1. GitHub → AWS: OIDC trust `aud=sts.amazonaws.com`, `sub` = `repo:SGit-AI/SGit-AI__API:environment:{dev,main,prod}` (`deploy/aws/github-oidc-role.cfn.yml:52-62`); no ref/workflow binding. Environment protection rules are not source-visible.
2. Deploy role → account: IAM actions on `role/sgit-vaults-*` incl. CreateRole/PutRolePolicy/AttachRolePolicy/PassRole with no boundary (`:98-103`); cloudformation:*/lambda:* on sgit-vaults-*; cloudfront:* and route53:ChangeResourceRecordSets on `*` (`:106-109`); s3 Put* on stage buckets.
3. Stage separation: single role for all stages; per-stage only by GitHub Environment name.
4. Dispatcher/PR author → privileged job shell: `${{ }}` interpolation into `run:`; same-repo PR code with `SG_NEW_TOKEN`.
5. Internet → deployed API: public Function URL; token gating of writes only; no reserved concurrency.

**Starting paths.** `deploy/aws/github-oidc-role.cfn.yml`, `deploy/aws/lambda.cfn.yml`, `deploy/aws/cloudfront_ensure_enabled.sh`, `deploy/docker/{Dockerfile,serve.py,requirements.txt}`, `.github/workflows/*.yml`, `tests/regression/*`, `tests/deploy/test_smoke__deployed_target.py`.

**Prior coverage.** No prior ledger exists for this repo.

**Companion selection.** SUPPLY-CHAIN-AND-RELEASE.md (CI is authorization code: privileged workflows, expression injection, mutable actions, build inputs); CLOUD-AND-DEPLOYMENT.md (OIDC/IAM overreach, cross-stage role confusion, public ingress, secret exposure, configuration fallback). Excluded: WEB-PROTOCOL-AND-AUTH (app-level auth is the origin package — Run A), CLIENT-SIDE (pages/ out of scope), others (no matching boundary).
