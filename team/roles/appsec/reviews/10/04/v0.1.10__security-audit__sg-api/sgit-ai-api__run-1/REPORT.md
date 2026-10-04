# Security audit — SGit-AI__API deploy lane (run 1)

## 1. Run profile and limits

| | |
|---|---|
| Target | `SGit-AI/SGit-AI__API` @ `e5f39f6` (branch `claude/sg-api-security-reviews-414dfx`; the only dirty path was the untracked audit skill itself) |
| Profile | **quick, scoped**: this is a **partial pass**, not complete coverage |
| Scope | `deploy/`, `.github/workflows/`, `tests/regression/`, `tests/deploy/`, `tests/unit/vault_conformance/` |
| Out of scope | `pages/`, `vault/`, `programme/`, `library/`, `team/`, and the origin application code (audited separately in the SGraph-AI__App__Send run) |
| Budget | 12 agent invocations; **11 spent**: 2 reconnaissance (the four baseline recon prompts were merged into two for this ~1.5k-line target, a deviation from the skill), 3 hunters, 1 final critic, 4 verifiers (quick profile: Phase 3 and Phase 5 merged) |
| Execution | Sandboxed source-and-local only. No AWS, GitHub API, or workflow runs. IaC and workflow claims were settled by static evaluation of the in-repo templates. The one shell fixture (the quote breakout) ran under `unshare -rn env -i timeout prlimit` with a dummy marker. No artifacts were promoted. |
| Prior runs | None; this is the first ledger for this repository. |

## 2. Posture

The application deploy path is well-intentioned:
- OIDC only, no long-lived AWS keys.
- The trust policy is pinned to this repo and three environment subjects.
- The bucket has public access blocked.
- The image runs as non-root.

The **deploy role's IAM grant undoes most of that**. Name-prefix scoping on IAM writes includes the role itself, so any job that can assume the role can make itself account administrator. Everything else in this report sits on top of that one problem or depends on GitHub Environment settings the repository cannot show.

## 3. Confirmed findings

| Severity | Title | Boundary | Observed (static) |
|---|---|---|---|
| **high** (impact critical, likelihood medium) | Deploy role can rewrite its own IAM permissions → AWS account admin | GitHub environment job → AWS account | `iam:AttachRolePolicy` on `role/sgit-vaults-github-deploy` evaluates to Allow under `Sid ExecutionRole`. There is no condition, boundary or deny. |

## 4. Confirmed finding detail

**Deploy role self-escalation**, `deploy/aws/github-oidc-role.cfn.yml:98-103` (fingerprint `deploy/aws/github-oidc-role.cfn.yml:DeployRole:iam-self-escalation-via-sgit-vaults-role-wildcard`)

- **Lower-trust principal:** anyone who can run a job in GitHub Environment `dev`, `main` or `prod`. In practice that is a repo writer pushing to `dev` or dispatching, or code running inside the deploy job.
- **How it escalates:** the role's own name `sgit-vaults-github-deploy` matches the `role/sgit-vaults-*` resource on `iam:CreateRole/PutRolePolicy/AttachRolePolicy/PassRole/UpdateRole`. The statement has no `iam:PolicyARN`, `iam:PermissionsBoundary` or `iam:PassedToService` condition, and DeployRole has no boundary.
  - A session can attach `AdministratorAccess` to itself.
  - Alternatively, it can write an admin policy onto `sgit-vaults-lambda--<stage>` and run code as that role through `lambda:*`.
- **README contradiction:** this directly contradicts `deploy/aws/README.md:49` ("cannot touch any resource not named sgit-vaults-*").
- **Conditions:** the bootstrap stack was deployed from this template, and no out-of-band SCP or boundary applies. Neither is visible in source.
- **Reproduction (static, no AWS calls):** render DeployRole with a dummy account ID. Match `arn:aws:iam::111122223333:role/sgit-vaults-github-deploy` against `role/sgit-vaults-*`. The request is allowed with no condition.
- **Smallest fix:** stop the deploy role from writing IAM policy it, or a role it can run code as, could use.
  - Preferred: deploy the stage stack through a CloudFormation service role (`--role-arn`) and keep only `iam:PassRole` on that role.
  - Otherwise: scope IAM writes to `role/sgit-vaults-lambda--*` and require `iam:PermissionsBoundary` on create/put/attach. Add `iam:PassedToService: lambda.amazonaws.com`, put the boundary on `ExecutionRole`, and add an explicit `Deny iam:*` on the deploy role's own ARN.
  - Narrowing the prefix alone is not enough. Full patch in `FINDINGS-DETAIL.md`.
- **Regression check:** add a policy check (cfn-guard or IAM simulator in CI) asserting that `iam:AttachRolePolicy` on `role/sgit-vaults-github-deploy` is an implicit deny.

## 5. Needs validation (no severity; these are leads, not confirmed vulnerabilities)

| Lead | Trace | Exact blocker | Safe owner check |
|---|---|---|---|
| One deploy role for dev/main/prod. A dev-environment job holds the prod stack, the prod function config (including its plaintext token), prod vault objects, and Route53/CloudFront on `*` | `deploy-aws__dev.yml:3` → `deploy-aws-lambda.yml:103,112` → `github-oidc-role.cfn.yml:60` → policies `:72,78,96,108` | GitHub Environment protection for dev/main vs prod; writers who are not prod reviewers; SCPs; other zones/distributions in the account | Settings → Environments; read-only `iam:SimulatePrincipalPolicy` against the prod function, bucket object and an unrelated hosted zone |
| Prod `workflow_dispatch` inputs are interpolated into the credentialed deploy shell (quote breakout reproduced locally with a dummy marker) | `deploy-aws__prod.yml:5,13` → `deploy-aws-lambda.yml:103,110,136` | The prod Environment's branch policy and reviewers. If prod accepts any branch, a writer already runs code there and this crosses no boundary | Settings → Environments → prod (branch rule, reviewers). **Never** dispatch with a test payload |
| Following the README can deploy prod with the access-token gate disabled behind a public Function URL, and the pipeline stays green | `lambda.cfn.yml:146,154` ← `deploy-aws__prod.yml:18` (caller job, no environment) → `deploy-aws-lambda.yml:131,135` → `lambda.cfn.yml:65,140` | Where `SGIT_VAULTS__ACCESS_TOKEN__PROD` is actually defined; GitHub's resolution of environment-only secrets in reusable-workflow caller jobs; the live prod env keys; operator intent | Secrets page; last prod run for the "OPEN instance" warning and skipped `test_5b`; `aws lambda get-function-configuration … --query 'keys(Environment.Variables)'` |

Full traces and plans are in `NEEDS-VALIDATION.md`.

## 6. Hardening notes (not findings)

- `deploy-aws-lambda.yml:69,131,135` interpolate secrets (`AWS_DEPLOY_ROLE_ARN`, `ACCESS_TOKEN`) directly into `run:` text. Pass them via `env:`; the same fix also closes the dispatch-input lead.
- `owasp-sbot/OSBot-GitHub-Actions@dev` is a mutable ref. It runs with `contents: write` (`ci-pipeline.yml:33,46`) and in `deploy-aws-lambda.yml:57`, where workflow-level `id-token: write` applies. Pin it to a SHA and move `id-token: write` to the deploy job only.
- `regression-parity.yml`:
  - It has no `permissions:` block and runs unpinned pip installs.
  - Its dispatch `new_url` can send the repository-level `SG_NEW_TOKEN` to any host. This is no privilege gain for writers, but move the token to an environment and allowlist hosts.
- The `cloudfront` job (`deploy-aws-lambda.yml:178-189`) assumes the role without `environment:`. Its OIDC sub will not match the trust policy, so it fails closed. This is a functional bug: add `environment: ${{ inputs.stage }}`.
- The OIDC trust has no `job_workflow_ref` or ref binding. Any workflow that declares `environment: dev` gets the role.
- The deploy role has `s3:Put*` on stage buckets, which includes `PutBucketPolicy`, `PutPublicAccessBlock` and `PutBucketAcl`. Narrow it to what CloudFormation needs. Object `Get*`/`Put*` contradicts README:44.
- The access token is stored in plaintext in the Lambda env (`lambda.cfn.yml:140`); `NoEcho` only hides the CloudFormation parameter. Prefer SSM SecureString or Secrets Manager with stage-scoped readers.
- Build inputs:
  - The Dockerfile installs unpinned dependencies with no `--require-hashes`.
  - The origin tarball is fetched with no digest check.
  - Base images are pinned by tag, not digest.
- The public Function URL bypasses any future edge control, and there is no reserved concurrency.
- `deploy-aws__dev`/`__main` `workflow_dispatch` from any ref deploys unmerged code unless Environment branch policies prevent it.

**Positive patterns:**
- OIDC with an exact-subject trust policy.
- Fork PRs cannot reach secrets (`pull_request`, not `_target`).
- The smoke suite only sends the stage token to the stack's own Function URL output.
- The bucket blocks public access and uses SSE.
- The container runs as uid 10001.
- `cloudfront_ensure_enabled.sh` quotes its arguments.

## 7. Coverage

| Status | Units |
|---|---|
| candidate | 3 (OIDC/IAM, workflows, runtime config) |
| covered / blocked | 0 |
| deferred (`quick_profile_final_critic`) | 2: deploy **lifecycle modes**, and the **static Pages projection** |

The deferred units are:
- **Deploy lifecycle modes:** bootstrap-stack self-update (the role's `cloudformation:*` on `stack/sgit-vaults-*` also matches its own bootstrap stack `sgit-vaults-github-oidc`), failed-deploy rollback, and teardown with a retained bucket.
- **Static Pages projection:** the committed read key, what `cp` publishes, and `pages: write` / `id-token: write` scope.

The final critic accepted those two gaps. No other critic ran, so **no clean-coverage claim is made**. A `standard` re-run should start with the two deferred units.
