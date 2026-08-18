[🏠 Deploy Hub](../../00-START-HERE.md) › **AWS Lambda**

# Deploy on AWS Lambda (serverless)

**Status: 🚧 templates written + lint-clean; live-account validation in progress.** The
template ships in the repo at `deploy/aws/lambda.cfn.yml`.

One CloudFormation stack: container-image Lambda + public Function URL. Pay-per-request,
scales to zero. Storage `s3` (durable) or `memory` (ephemeral).

```bash
# image must be in YOUR ECR (Lambda requirement) — see deploy/aws/README.md for the 4 commands
aws cloudformation deploy --template-file deploy/aws/lambda.cfn.yml \
  --stack-name sg-send-lambda --capabilities CAPABILITY_IAM \
  --parameter-overrides ImageUri=<acct>.dkr.ecr.<region>.amazonaws.com/sg-send-vault:latest \
                        MemorySize=1024 AccessToken=$(openssl rand -hex 32)
```

Key parameters: `MemorySize` (128–10240), `Timeout`, `StorageMode` (s3|memory),
`AccessToken` (your licensing key — gates everything incl. reads; keep it in a password
manager or an SG/Vault), and the custom-domain trio (`DomainName`+`HostedZoneId`+
`CertificateArn` — cert must be in **us-east-1**).

Then: open the `PublicUrl` output → sign in → or
`sgit clone <vault-key> --endpoint <PublicUrl> --token <access-key>`.

First set up your account: [AWS account setup](../../runbooks/new-aws-account/README.md).
