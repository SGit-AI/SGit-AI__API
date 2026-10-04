# Needs validation — SGit-AI__API deploy lane (run 1)

These are source-grounded leads with an exact unresolved fact. They carry **no severity** and are not confirmed vulnerabilities. Never resolve them by sending audit traffic to a deployment.

## One deploy role for dev/main/prod: a dev-Environment job holds the prod stack, prod function config/token, prod vault bucket objects and account-wide DNS/CloudFront authority

Fingerprint `deploy/aws/github-oidc-role.cfn.yml:DeployRole:single-role-all-stages-no-stage-binding`

The bootstrap template creates a single OIDC role, sgit-vaults-github-deploy. Its trust policy accepts environment:dev, environment:main and environment:prod for this repository (github-oidc-role.cfn.yml:59-62), and the inline permission policy has no statement that depends on which subject assumed it: no per-stage role, no session-tag or sub-claim condition, no stage component in any resource ARN. cloudformation:* covers stack/sgit-vaults-*/*, which includes sgit-vaults-api--prod. lambda:* covers function:sgit-vaults-*, which includes sgit-vaults-api--prod (lambda.cfn.yml:123); GetFunctionConfiguration on it returns the prod SGRAPH_SEND__ACCESS_TOKEN (lambda.cfn.yml:140). s3:Get*/Put* covers {account}--sgit-vaults--*/*, including the prod bucket (lambda.cfn.yml:79), so GetObject/PutObject on prod vault ciphertext are allowed, contradicting the README claim that object reads and writes belong to the function's role. The Edge statement allows cloudfront:* and route53:ChangeResourceRecordSets on '*'. Any job that obtains an environment:dev token (push to dev, dispatch of the dev workflow, or any branch workflow declaring environment: dev) therefore gets prod-equivalent authority, which bypasses the required reviewers the README tells operators to put on the prod Environment as the 'two-person' control. This root cause is distinct from the execution-role self-escalation candidate: the cross-stage reach is granted directly by stage-unbound resource ARNs with no IAM escalation, and the fix differs (per-stage roles or ARNs rather than a permissions boundary). Exploitability depends on GitHub Environment protection settings and on the account's other resources and guardrails, none of which are source-visible.

**Claimed root cause.** Stage separation exists only as the GitHub Environment name in the OIDC sub claim (github-oidc-role.cfn.yml:59-62). The single role's permission statements (lines 69-109) are not conditioned on that claim, and their resource ARNs use stage wildcards that also match the prod stack, function and bucket; the Edge statement grants cloudfront:* and route53:ChangeResourceRecordSets on '*'.

### Trace

1. `.github/workflows/deploy-aws__dev.yml:3` (entrypoint, on.push / workflow_dispatch): A push to dev or a manual dispatch by a repository writer starts the dev deploy; no approval gate in source.
2. `.github/workflows/deploy-aws__dev.yml:11` (propagation, jobs.dev.with.stage): Passes stage: dev to the reusable deploy workflow.
3. `.github/workflows/deploy-aws-lambda.yml:103` (propagation, jobs.deploy.environment): Deploy job runs in Environment dev (auto-created; reviewers intended on prod only), so the OIDC sub is repo:SGit-AI/SGit-AI__API:environment:dev.
4. `.github/workflows/deploy-aws-lambda.yml:112` (propagation, jobs.deploy.steps[configure-aws-credentials]): Assumes the same role (AWS_DEPLOY_ROLE_ARN) that main and prod use.
5. `deploy/aws/github-oidc-role.cfn.yml:60` (propagation, DeployRole.AssumeRolePolicyDocument): Trust admits environment:dev, and environment:main/prod (61-62) on the same role.
6. `deploy/aws/github-oidc-role.cfn.yml:72` (propagation, DeployRole.Policies.sgit-vaults-deploy.Stacks): cloudformation:* on stack/sgit-vaults-*/* matches sgit-vaults-api--prod.
7. `deploy/aws/github-oidc-role.cfn.yml:78` (propagation, DeployRole.Policies.sgit-vaults-deploy.LambdaAndLogs): lambda:* on function:sgit-vaults-* matches the prod function, including GetFunctionConfiguration (prod token) and UpdateFunctionCode/Configuration.
8. `deploy/aws/github-oidc-role.cfn.yml:96` (propagation, DeployRole.Policies.sgit-vaults-deploy.Buckets): s3:Get*/Put* on {account}--sgit-vaults--*/* covers prod vault objects.
9. `deploy/aws/github-oidc-role.cfn.yml:108` (sink, DeployRole.Policies.sgit-vaults-deploy.Edge): cloudfront:* and route53:ChangeResourceRecordSets on Resource '*' (line 109) cover every distribution and hosted zone in the account.

### Evidence

- `deploy/aws/lambda.cfn.yml:79`: Prod bucket name {account}--sgit-vaults--{region}--prod matches the deploy role's S3 wildcard.
- `deploy/aws/lambda.cfn.yml:123`: Prod function name sgit-vaults-api--prod matches lambda:* wildcard.
- `deploy/aws/lambda.cfn.yml:140`: Prod access token stored as plaintext Lambda env var, readable via lambda:GetFunctionConfiguration.
- `deploy/aws/README.md:44`: Says object reads and writes are the function's role, not the deploy role's; the policy contradicts this.
- `deploy/aws/README.md:69`: Required reviewers on prod described as what makes a prod deploy a two-person act; that only gates environment:prod.
- `deploy/aws/github-oidc-role.cfn.yml:69`: No statement in lines 69-113 has a Condition, stage-specific ARN, or session-tag requirement.

### Blockers

- Actual GitHub Environment protection settings for dev and main (required reviewers, deployment branch/tag policies) are not source-visible; if dev/main are protected as strictly as prod the review-gate bypass disappears, though over-breadth remains.
- Whether the repository has writers/dispatchers who are not prod-Environment reviewers is not visible.
- Account-level guardrails (SCPs, out-of-band permissions boundary, prod bucket policy) are not visible.
- Whether the account holds other Route53 hosted zones or CloudFront distributions that the Edge '*' grant would expose is not visible.

### Resolution plan

- **Local (bounded):** Render github-oidc-role.cfn.yml with default parameters, confirm no Statement in sgit-vaults-deploy has a Condition, and match the resource ARNs against the prod names in lambda.cfn.yml (stack sgit-vaults-api--prod, function sgit-vaults-api--prod, bucket <acct>--sgit-vaults--eu-west-2--prod/*) with IAM wildcard semantics using a stdlib fnmatch fixture. Expect all to match for lambda:GetFunctionConfiguration, s3:GetObject and cloudformation:UpdateStack.
- **Owner-observed:** Owner observes, without audit traffic: (1) GitHub Settings → Environments protection rules and branch policies for dev, main, prod, and prod reviewers vs users with write access; (2) the effective IAM policy of sgit-vaults-github-deploy, any permissions boundary and applicable SCPs; (3) whether the prod bucket policy denies the deploy role object access; (4) Route53 hosted zones and CloudFront distributions unrelated to sgit-vaults. Optionally run read-only iam:SimulatePrincipalPolicy for the role against the prod function (lambda:GetFunctionConfiguration) and prod bucket object (s3:GetObject).

## Following the README can deploy the prod stage with the API access-token gate disabled behind a public Function URL, and the pipeline still goes green

Fingerprint `deploy/aws/lambda.cfn.yml:AccessToken-empty-default-fail-open-prod`

The prod caller workflow passes secrets.SGIT_VAULTS__ACCESS_TOKEN__PROD into the reusable deploy workflow from a caller job (jobs.prod with uses:) that declares no environment, while deploy/aws/README.md:67 tells operators to put this secret in the prod GitHub Environment. GitHub documents that a caller job without an environment cannot read environment-scoped secrets, and the environment-bound deploy job reads only secrets.ACCESS_TOKEN, so an operator following the README probably gets an empty ACCESS_TOKEN. The workflow then prints only a ::warning and passes AccessToken="" to CloudFormation; HasAccessToken is false, SGRAPH_SEND__ACCESS_TOKEN is unset, no SGRAPH_SEND__ADMIN__BASE_URL is set, and the Function URL is AuthType NONE with Principal '*'. In the origin package served by the image, no admin base URL plus an empty env token means the access-token check allows every request, so write, batch, presigned and transfer routes accept anonymous internet callers on prod. The verify job's gate tests skip when the token is empty and the roundtrip write then succeeds, so the run is green. The open mode is documented ('Empty = explicitly open instance'), so a deliberately empty token is an intended mode; the defect is that the README's prod instruction is likely not reachable from the workflow as written, and a misconfigured prod deploys open with only a warning. Whether this happens depends on hosted-platform secret resolution and where the secret is actually defined.

**Claimed root cause.** (1) The prod caller (.github/workflows/deploy-aws__prod.yml:9-18) reads the prod token in a reusable-workflow caller job with no environment while the README places it in the prod Environment, and the environment-bound deploy job reads only secrets.ACCESS_TOKEN. (2) An empty token fails open with no hard stop for prod: lambda.cfn.yml defaults AccessToken to '' (:42-46), HasAccessToken (:65) false leaves SGRAPH_SEND__ACCESS_TOKEN unset (:140), the workflow only warns (deploy-aws-lambda.yml:131), the smoke gate tests skip (tests/deploy/test_smoke__deployed_target.py:54,60), and the Function URL is public (lambda.cfn.yml:146,154).

### Trace

1. `deploy/aws/lambda.cfn.yml:146` (entrypoint, FunctionUrl resource): Function URL created with AuthType NONE; anonymous internet callers reach the API.
2. `deploy/aws/lambda.cfn.yml:154` (propagation, FunctionUrlPublicAccess permission): lambda:InvokeFunctionUrl granted to Principal '*'; the app token is the only gate.
3. `.github/workflows/deploy-aws__prod.yml:18` (propagation, jobs.prod (reusable-workflow caller, no environment)): Passes secrets.SGIT_VAULTS__ACCESS_TOKEN__PROD as ACCESS_TOKEN from a job with no environment; an Environment-only secret is expected to resolve empty.
4. `.github/workflows/deploy-aws-lambda.yml:131` (propagation, jobs.deploy, step 'CloudFormation deploy'): Empty ACCESS_TOKEN only emits ::warning and deployment continues, including for prod.
5. `.github/workflows/deploy-aws-lambda.yml:135` (propagation, jobs.deploy, step 'CloudFormation deploy'): Passes AccessToken="" as a parameter override.
6. `deploy/aws/lambda.cfn.yml:65` (propagation, Conditions.HasAccessToken): HasAccessToken is false when AccessToken is ''.
7. `deploy/aws/lambda.cfn.yml:140` (sink, VaultsFunction.Properties.Environment.Variables): SGRAPH_SEND__ACCESS_TOKEN becomes AWS::NoValue and no admin base URL is set: the origin app's 'no token configured, allow all' fallback.

### Evidence

- `deploy/aws/lambda.cfn.yml:46`: AccessToken description 'Empty = explicitly open instance'; default '' (line 44).
- `deploy/aws/README.md:67`: Prod token row says to put it in the prod Environment's secrets.
- `.github/workflows/deploy-aws-lambda.yml:103`: Only the inner deploy job binds environment; it reads secrets.ACCESS_TOKEN, never the stage-named secret.
- `tests/deploy/test_smoke__deployed_target.py:54`: Write-gate test skips when the token is empty; the run stays green.
- `deploy/docker/serve.py:19`: The image serves the origin package's User app, whose env fallback allows all when the token is empty and no admin client exists.

### Blockers

- Where SGIT_VAULTS__ACCESS_TOKEN__PROD is actually defined (repository secret vs prod Environment only), and whether prod defines a secret named ACCESS_TOKEN.
- GitHub's effective resolution of an environment-only secret referenced from a reusable-workflow caller job without an environment (hosted-platform behaviour).
- Whether stack sgit-vaults-api--prod is deployed and its live Lambda configuration lacks SGRAPH_SEND__ACCESS_TOKEN and SGRAPH_SEND__ADMIN__BASE_URL.
- Whether an empty prod token is operator intent (documented open mode) or misconfiguration; the finding holds only for the latter.

### Resolution plan

- **Local (bounded):** Statically evaluate deploy/aws/lambda.cfn.yml with AccessToken='' and Stage=prod (YAML loader treating CFN tags as data, under unshare -rn env -i timeout prlimit): HasAccessToken false, SGRAPH_SEND__ACCESS_TOKEN resolves to AWS::NoValue, no SGRAPH_SEND__ADMIN__BASE_URL key, FunctionUrl.AuthType NONE. Confirm jobs.prod in deploy-aws__prod.yml has no environment: key.
- **Owner-observed:** Owner-observed, read-only: (1) whether SGIT_VAULTS__ACCESS_TOKEN__PROD is a repository secret or only under Environments > prod; (2) whether the latest 'Deploy AWS — prod' run shows the 'ACCESS_TOKEN secret not set' warning and skipped test_5b/test_5; (3) aws lambda get-function-configuration --function-name sgit-vaults-api--prod --query 'keys(Environment.Variables)' to record only whether SGRAPH_SEND__ACCESS_TOKEN and SGRAPH_SEND__ADMIN__BASE_URL are present. Do not send audit traffic to the prod Function URL.

## Prod workflow_dispatch inputs are textually interpolated into the credentialed CloudFormation deploy shell (expression injection)

Fingerprint `github-workflows/deploy-aws-lambda.yml:cloudformation-deploy:dispatch-input-expression-injection`

deploy-aws__prod.yml takes three free-text workflow_dispatch inputs (domain_name, hosted_zone_id, certificate_arn) and forwards them unvalidated into the reusable deploy-aws-lambda.yml, where the deploy job (environment: prod, after configure-aws-credentials assumes the OIDC deploy role) expands them with ${{ inputs.* }} directly into the bash text of the 'CloudFormation deploy' step, inside double quotes and in the same script that inlines secrets.ACCESS_TOKEN. A value containing a double quote breaks out of the quoting and runs arbitrary shell in the prod-environment job, which holds the deploy-role AWS credentials and the prod API token. The quote breakout was reproduced with a harmless local fixture (lines 131-136 rendered by literal substitution, aws stubbed, under unshare -rn env -i with timeout and prlimit; a dummy marker printed). Only principals who can already dispatch workflows (repo write) can supply inputs, so this crosses a boundary only if the prod Environment is restricted (deployment branch policy limited to protected refs and/or required reviewers approving reviewed code); if prod accepts any branch, a writer can already run arbitrary code there and the injection adds nothing.

**Claimed root cause.** deploy-aws-lambda.yml:136 expands ${{ inputs.domain_name }}, ${{ inputs.hosted_zone_id }} and ${{ inputs.certificate_arn }} directly into run: shell text instead of passing them through env:, and deploy-aws__prod.yml:5-7 declares them as free-text inputs with no validation anywhere; the step runs in the prod-environment deploy job after the OIDC role is assumed (:103, :110-113) and inlines secrets.ACCESS_TOKEN (:131, :135).

### Trace

1. `.github/workflows/deploy-aws__prod.yml:5` (entrypoint, workflow_dispatch inputs): Free-text dispatch input domain_name (also hosted_zone_id :6, certificate_arn :7); only repo writers can dispatch.
2. `.github/workflows/deploy-aws__prod.yml:13` (propagation, jobs.prod (uses deploy-aws-lambda.yml)): Forwards the inputs unchanged (:13-15) with stage: prod and the prod access-token secret.
3. `.github/workflows/deploy-aws-lambda.yml:103` (propagation, jobs.deploy): Job runs in GitHub Environment prod, the OIDC subject the deploy role trusts and the only place a protection rule applies.
4. `.github/workflows/deploy-aws-lambda.yml:110` (propagation, jobs.deploy steps: configure-aws-credentials): Assumes the deploy role via OIDC so later steps hold its credentials.
5. `.github/workflows/deploy-aws-lambda.yml:136` (sink, jobs.deploy steps: CloudFormation deploy (run:)): DomainName="${{ inputs.domain_name }}" HostedZoneId="${{ inputs.hosted_zone_id }}" CertificateArn="${{ inputs.certificate_arn }}" are substituted as text into bash; a double quote ends the string and injects commands.

### Evidence

- `.github/workflows/deploy-aws-lambda.yml:131`: Same script inlines ${{ secrets.ACCESS_TOKEN }} (also :135).
- `.github/workflows/deploy-aws-lambda.yml:103`: Only a comment suggests reviewers on prod; no branch policy or reviewers are enforced in source.
- `deploy/aws/github-oidc-role.cfn.yml:59`: Role trust limited by sub to environment:dev/main/prod (:59-62) with no ref/workflow binding.
- `deploy/aws/github-oidc-role.cfn.yml:101`: Privilege available to injected code: IAM writes on role/sgit-vaults-* and cloudfront:*/route53 on * (:101-109).
- `.github/workflows/deploy-aws__prod.yml:3`: workflow_dispatch is the only trigger.

### Blockers

- The prod GitHub Environment's deployment branch/tag policy is not source-visible; if prod accepts any branch the injection crosses no boundary.
- Whether prod has required reviewers, and whether the approval UI shows dispatch input values to reviewers, is hosted-platform configuration/behaviour.
- The set of principals with write/dispatch rights versus those able to merge to main is not source-visible.

### Resolution plan

- **Local (bounded):** Copy deploy-aws-lambda.yml lines 131-136 into a scratch script, substitute ${{ inputs.domain_name }} with 'vaults.example.test" ; echo INJECTED_MARKER_DUMMY ; : "', stub aws() as echo, and run under unshare -rn env -i timeout 5 prlimit --as=200000000 /bin/bash; the marker prints after the stub (already reproduced). After the fix (inputs via env: and "$DOMAIN_NAME"), the same payload must reach aws as one argument and the marker must not print.
- **Owner-observed:** A repository owner observes, without dispatching any workflow, Settings > Environments > prod: the deployment branches/tags rule, required reviewers, and whether prod secrets/role ARN are environment-scoped; and which principals have write/dispatch access but cannot merge to the refs prod allows. Never trigger the prod workflow with a test payload.
