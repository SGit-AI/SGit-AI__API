# Deploying the sgit vaults API to AWS

One image, three Lambda stacks — `dev`, `main`, `prod` — mirroring the three User Lambdas the
origin repo deploys (`user-dev` on push to `dev`, `user-main` on push to `main`, `user-prod`
by manual dispatch). GitHub OIDC only; no AWS keys anywhere.

| Stage | Trigger | Stack | Function | Bucket |
|---|---|---|---|---|
| dev  | push to `dev` (or dispatch) | `sgit-vaults-api--dev`  | `sgit-vaults-api--dev`  | `{account}--sgit-vaults--{region}--dev` |
| main | push to `main` (or dispatch) | `sgit-vaults-api--main` | `sgit-vaults-api--main` | `…--main` |
| prod | manual dispatch, GitHub Environment `prod` (add required reviewers there) | `sgit-vaults-api--prod` | `sgit-vaults-api--prod` | `…--prod` |

Each run: unit tests → build the API-only image → self-contained boot check (no network) →
push to ECR → CloudFormation deploy → **smoke suite** against the Function URL → **parity gate**
(the API as it runs today, in-process, vs the deployed stack; and via the edge when a custom
domain exists) → **CloudFront enabled check** (enables a disabled distribution, warns on any
error-page rewrite) → a deployment record in the run summary.

## One-time account setup (you, ~10 minutes, admin credentials)

### 1. Create the deploy role — the exact IAM the pipeline needs

```bash
aws cloudformation deploy \
  --template-file deploy/aws/github-oidc-role.cfn.yml \
  --stack-name sgit-vaults-github-oidc \
  --capabilities CAPABILITY_NAMED_IAM
# if the account already has the GitHub OIDC provider (only one per account):
#   --parameter-overrides CreateOidcProvider=false
aws cloudformation describe-stacks --stack-name sgit-vaults-github-oidc \
  --query 'Stacks[0].Outputs[?OutputKey==`RoleArn`].OutputValue' --output text
```

What the role is, precisely (`deploy/aws/github-oidc-role.cfn.yml`):

- **Trust:** `sts:AssumeRoleWithWebIdentity` from GitHub's OIDC provider, **only** for
  `repo:SGit-AI/SGit-AI__API` and only from three subjects: `environment:dev`, `environment:main`,
  `environment:prod` (the deploy job runs inside the stage's GitHub Environment, so the token
  carries that claim). A fork, a pull request, or a job outside those environments cannot assume it. Sessions last at most one hour and are minted per job; nothing is stored.
- **Permissions, all name-scoped where the service allows it:**
  - CloudFormation on stacks named `sgit-vaults-*`
  - Lambda + CloudWatch Logs on `sgit-vaults-*` functions and their log groups
  - ECR on the one repository `sgit-vaults-api` (+ the resource-less `GetAuthorizationToken`)
  - S3 bucket-level actions on `{account}--sgit-vaults--*` (create/configure); object reads
    and writes are the *function's* role, not this one
  - IAM create/attach/pass on roles named `sgit-vaults-*` (the function's execution role)
  - CloudFront + the three Route53 record actions + ACM list/describe (custom domain and the
    enabled-check; CloudFront has no resource-level scoping)
- **What it cannot do:** touch any resource not named `sgit-vaults-*`, create users or keys,
  read secrets, reach the origin repo's `sg-send-*` / `sgraph-ai-app-send--*` resources.

### 2. Why this is more secure than API keys

The pipeline never holds a credential. Each job presents a short-lived GitHub-signed token;
AWS checks the repository and ref in it and issues a one-hour session for this role only.
There is nothing to leak, rotate, or revoke besides the role itself, and CloudTrail records
every call under the role with the GitHub run as the session name. The origin repo's pipeline
used four long-lived secrets (`AWS_ACCESS_KEY_ID` …); this one uses zero.

### 3. GitHub secrets (Settings → Secrets and variables → Actions)

| Secret | Value | Required |
|---|---|---|
| `AWS_DEPLOY_ROLE_ARN` | the `RoleArn` output from step 1 | yes — without it every deploy job skips and says so |
| `SGIT_VAULTS__ACCESS_TOKEN__DEV` | the dev stage's access token (`openssl rand -hex 32`) | no — empty deploys an **open** instance, loudly |
| `SGIT_VAULTS__ACCESS_TOKEN__MAIN` | | same |
| `SGIT_VAULTS__ACCESS_TOKEN__PROD` | | same; put it in the `prod` Environment's secrets |

Then create the GitHub Environment `prod` (Settings → Environments) with required reviewers:
that is what makes the prod deploy a two-person act. The role's trust policy only accepts the
`environment:prod` subject for that stage.

### 4. Region

`eu-west-2` (London), set once in `deploy-aws-lambda.yml`. A second region is the same
workflow with a different `AWS_REGION`; the bucket and stack names already carry the region.

## What gets deployed today

Until phase-1 step 1.3 lands the code in this repo, the image serves the vault API from the
**origin package at the baseline commit** (`sgraph-ai-app-send` from the git archive of
`ORIGIN_COMMIT` in the Dockerfile — PyPI only carries major releases) — the same app
that runs on `dev.send.sgraph.ai`, booted standalone, API only (no UI overlay, no Send UIs).
`deploy/docker/serve.py` switches to `sgit_vaults` the moment it is importable; the pipeline,
the templates, the gates and the role do not change. That is the point of building the lane
first: the move lands into a pipeline that is already proven live.

## Custom domain (`vaults.sgit.ai`)

Pass `domain_name`, `hosted_zone_id` and an ACM certificate ARN **in us-east-1** to the prod
dispatch (or set them in the dev/main callers). The stack then adds a CloudFront distribution
in front of the Function URL and a Route53 alias. The distribution deliberately has **no custom
error responses**: the origin repo's edge rewrote API 403s into a 404 page (pack Q11); this one
passes status codes through, and the enabled-check step warns if that ever changes.

## Teardown

```bash
aws cloudformation delete-stack --stack-name sgit-vaults-api--dev
```
removes everything except the data bucket (retained by policy — empty and delete it yourself
if you mean it). The ECR repository and the OIDC role are shared across stages and stay.

## Run the gates yourself against any deployment

```bash
pip install -r tests/regression/requirements.txt
SG_BASE_URL=https://<function-url>/ SG_ACCESS_TOKEN=<token> SG_EXPECT_UI=false  python -m pytest tests/deploy -q
SG_LEGACY_URL=inprocess SG_NEW_URL=https://<function-url>/ SG_NEW_TOKEN=<token> python -m pytest tests/regression -q
```
