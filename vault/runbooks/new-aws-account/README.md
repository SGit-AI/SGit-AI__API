[🏠 Deploy Hub](../../00-START-HERE.md) › **AWS account setup**

# Set Up Your AWS Account for SG/Send

The one-time changes an AWS account needs before the SG/Send pipelines and templates can
deploy into it. Total time: ~15 minutes, no console clicking beyond what's listed.

## 1. One-time: create the GitHub OIDC deploy role

The pipelines authenticate via GitHub OIDC — **no long-lived AWS keys anywhere**. Deploy the
bootstrap template once (any admin credentials):

```bash
aws cloudformation deploy \
  --template-file deploy/aws/github-oidc-role.cfn.yml \
  --stack-name sg-send-github-oidc \
  --capabilities CAPABILITY_NAMED_IAM
```

If the account already has the `token.actions.githubusercontent.com` OIDC provider
(only one per account is allowed), add `--parameter-overrides CreateOidcProvider=false`.

Grab the role ARN:

```bash
aws cloudformation describe-stacks --stack-name sg-send-github-oidc \
  --query 'Stacks[0].Outputs[?OutputKey==`RoleArn`].OutputValue' --output text
```

## 2. One-time: set the GitHub secret

In the repo (Settings → Secrets and variables → Actions), create:

| Secret | Value |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | the RoleArn from step 1 |

That is the only AWS secret the new pipelines need. Without it, the deploy jobs skip
gracefully (image build + lint still run).

## 3. Verify: run the full cycle

From the repo's Actions tab, dispatch **Deploy Full Cycle** with `targets=lambda`.
The run will: build the image → prove the self-contained invariant → push to ECR (creating
the `sg-send-vault` repo if needed) → deploy the Lambda stack → run the smoke suite against
the live Function URL → destroy the stack → assert the account is clean.

Green run = the account is fully set up.

## 4. Optional: custom-domain prerequisites

Only needed when you want `send.yourdomain.com` instead of the generated URLs:

| Deployment | What you need in the account |
|---|---|
| Lambda (CloudFront) | Route53 hosted zone + ACM certificate **in us-east-1** |
| Fargate (ALB) | Route53 hosted zone + ACM certificate **in the stack's region** |
| EC2 (caddy) | Route53 hosted zone only — caddy gets its own Let's Encrypt cert |

## What each stack creates (and removes on delete)

| Stack | Creates | On delete |
|---|---|---|
| `lambda.cfn.yml` | Lambda fn, Function URL, IAM role, S3 bucket (s3 mode), optional CloudFront+DNS | everything except the S3 bucket (retained) |
| `ec2.cfn.yml` | instance, EIP, security group, IAM profile, EBS data volume, optional DNS | everything; data volume becomes a **snapshot** |
| `ecs-fargate.cfn.yml` | its own VPC, cluster, service, ALB, logs, IAM | **everything** including the VPC |

## Security posture

- The deploy role is scoped to `sg-send-*`/`sgsend-*` stacks and roles.
- Access tokens are **startup parameters** — never stored in SSM/Secrets Manager/disk.
- The server only ever stores ciphertext; keys never leave the client.
