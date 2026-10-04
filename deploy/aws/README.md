# Deploying the sgit vaults API to AWS

One image, three Lambda stacks — `dev`, `main`, `prod` — mirroring the three User Lambdas the
origin repo deploys (`user-dev` on push to `dev`, `user-main` on push to `main`, `user-prod`
by manual dispatch). GitHub OIDC only; no AWS keys anywhere. **One deploy role per stage**, each
assumable only from that stage's GitHub Environment, each able to touch that stage's resources only.

| Stage | Trigger | GitHub Environment | Role | Stack / function | Bucket |
|---|---|---|---|---|---|
| dev  | push to `dev` (or dispatch) | `dev` | `sgit-vaults-github-deploy--dev` | `sgit-vaults-api--dev` | `{account}--sgit-vaults--{region}--dev` |
| main | push to `main` (or dispatch) | `main` | `…--main` | `…--main` | `…--main` |
| prod | manual dispatch | `prod` (add required reviewers) | `…--prod` | `…--prod` | `…--prod` |

Each run: unit tests → build the API-only image → self-contained boot check (no network) → then,
**in one job inside the stage's Environment**: push to ECR → CloudFormation deploy → **smoke suite**
against the Function URL → **parity gate** (the API as it runs today, in-process, vs the deployed
stack; and via the edge when a custom domain exists) → **CloudFront enabled check** (enables a
disabled distribution, warns on any error-page rewrite) → a deployment record in the run summary.
One job holds the credentials, so prod's required reviewers are asked exactly once per deploy.

## One-time account setup (you, ~15 minutes, admin credentials)

### 1. Create the deploy roles — the exact IAM the pipeline needs

Three stacks from one template, one per stage. The first one also creates the GitHub OIDC
provider and the shared permissions boundary:

```bash
aws cloudformation deploy --template-file deploy/aws/github-oidc-role.cfn.yml \
  --stack-name sgit-vaults-github-oidc--dev  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides Stage=dev CreateOidcProvider=true CreateSharedResources=true
# CreateOidcProvider=false if the account already has the token.actions.githubusercontent.com provider
aws cloudformation deploy --template-file deploy/aws/github-oidc-role.cfn.yml \
  --stack-name sgit-vaults-github-oidc--main --capabilities CAPABILITY_NAMED_IAM --parameter-overrides Stage=main
aws cloudformation deploy --template-file deploy/aws/github-oidc-role.cfn.yml \
  --stack-name sgit-vaults-github-oidc--prod --capabilities CAPABILITY_NAMED_IAM --parameter-overrides Stage=prod
for s in dev main prod; do aws cloudformation describe-stacks --stack-name sgit-vaults-github-oidc--$s \
  --query 'Stacks[0].Outputs[?OutputKey==`RoleArn`].OutputValue' --output text; done
```

What each role is, precisely (`deploy/aws/github-oidc-role.cfn.yml`; pinned by
`tests/unit/deploy/test_deploy_templates.py`, which fails if any of this regresses):

- **Trust:** `sts:AssumeRoleWithWebIdentity` from GitHub's OIDC provider, for exactly one
  subject: `repo:SGit-AI/SGit-AI__API:environment:<stage>`. A fork, a pull request, a job outside
  that Environment, or another stage's job cannot assume it. Sessions last at most one hour and
  are minted per job; nothing is stored.
- **Permissions, all scoped to the stage's own names:**
  - CloudFormation on the one stack `sgit-vaults-api--<stage>` (not the bootstrap stacks)
  - Lambda + CloudWatch Logs on `sgit-vaults-api--<stage>` and its log group
  - ECR on the one shared repository `sgit-vaults-api` (+ the resource-less `GetAuthorizationToken`)
  - S3 **bucket-level** create/configure on `{account}--sgit-vaults--*--<stage>`: no object
    actions (vault ciphertext is the function's business), no bucket policy / ACL / public-access changes
  - IAM on the one execution role `sgit-vaults-lambda--<stage>`, and creating or editing it is
    allowed **only with the permissions boundary `sgit-vaults-lambda-boundary` attached**; `PassRole`
    only to `lambda.amazonaws.com`
  - CloudFront + the three Route53 record actions + ACM list/describe (custom domain and the
    enabled-check; CloudFront has no resource-level scoping, so this is the one account-wide grant)
- **Explicit denies:** any `iam:*` on any `sgit-vaults-github-deploy--*` role (a deploy role can
  never edit itself or a sibling), and removing or rewriting the boundary or any policy.
- **The boundary** (`sgit-vaults-lambda-boundary`, the ceiling for every execution role): logs
  for `/aws/lambda/sgit-vaults-*` and objects in the `sgit-vaults` buckets. Whatever a deploy job
  writes into the execution role, the function can never do more than that.
- **What a role cannot do:** become account admin (the 4 Oct 2026 security audit found the
  previous single-role version could, by rewriting its own policy — fixed and pinned by test),
  reach another stage's stack / function / bucket / token, read or write vault objects, create
  users or keys, read secrets, or touch the origin repo's `sg-send-*` resources.

### 2. Why this is more secure than API keys

The pipeline never holds a credential. Each job presents a short-lived GitHub-signed token;
AWS checks the repository and the Environment in it and issues a one-hour session for that
stage's role only. There is nothing to leak, rotate, or revoke besides the role itself, and
CloudTrail records every call under the role with the GitHub run as the session name. The
origin repo's pipeline used four long-lived secrets (`AWS_ACCESS_KEY_ID` …); this one uses zero.

### 3. GitHub Environments and their secrets (Settings → Environments)

Create the three Environments `dev`, `main`, `prod`, and in **each** add the same two
**Environment secrets** (not repository secrets — the deploy job reads them inside the Environment,
which is what keeps prod's values out of dev's reach):

| Environment secret | Value | Required |
|---|---|---|
| `AWS_DEPLOY_ROLE_ARN` | that stage's `RoleArn` output from step 1 | yes — without it the deploy job stops and says so (tests + image build still run) |
| `SGIT_VAULTS__ACCESS_TOKEN` | that stage's API access token (`openssl rand -hex 32`) | yes — an empty token **fails the deploy**. To run a stage open on purpose, dispatch with `open_instance=true` |

On `prod`, add required reviewers and a deployment-branch rule (`main` only): that is what makes
the prod deploy a two-person act, and the role's trust policy only accepts the `environment:prod`
subject for that stage.

### 4. Region

`eu-west-2` (London), set once in `deploy-aws-lambda.yml`. A second region is the same
workflow with a different `AWS_REGION`; the bucket and stack names already carry the region.

## What gets deployed today

Until phase-1 step 1.3 lands the code in this repo, the image serves the vault API from the
**origin package at the baseline commit** (`sgraph-ai-app-send` from the git archive of
`ORIGIN_COMMIT` in the Dockerfile — PyPI only carries major releases) — the same app
that runs on `dev.send.sgraph.ai`, booted standalone, API only (no UI overlay, no Send UIs).
`deploy/docker/serve.py` switches to `sgit_vaults` the moment it is importable; the pipeline,
the templates, the gates and the roles do not change. That is the point of building the lane
first: the move lands into a pipeline that is already proven live.

The security audit of 4 Oct 2026 (`team/roles/appsec/reviews/10/04/`) confirmed defects in
that origin package which this lane inherits until the move fixes them — read its
`VERIFICATION.md` before pointing real users at a stage.

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
if you mean it). The ECR repository, the boundary and the deploy roles are bootstrap resources and stay.

## Run the gates yourself against any deployment

```bash
pip install -r tests/regression/requirements.txt
SG_BASE_URL=https://<function-url>/ SG_ACCESS_TOKEN=<token> SG_EXPECT_UI=false  python -m pytest tests/deploy -q
SG_LEGACY_URL=inprocess SG_NEW_URL=https://<function-url>/ SG_NEW_TOKEN=<token> python -m pytest tests/regression -q
python -m pytest tests/unit/deploy -q          # the IAM / workflow policy invariants (no AWS needed)
```
