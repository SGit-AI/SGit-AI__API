[🏠 Deploy Hub](../../00-START-HERE.md) › **New region**

# Deploy SG/Send into a New AWS Region

Everything in SG/Send derives from `{account}` + `{region}` — nothing in the templates is
region-specific. A new region is the same commands with a different `--region`:

```bash
export AWS_DEFAULT_REGION=eu-central-1   # the new region

# 1. Get the image into the region's ECR (Lambda only)
aws ecr create-repository --repository-name sg-send-vault
docker pull diniscruz/sg-send-vault:latest
docker tag  diniscruz/sg-send-vault:latest <acct>.dkr.ecr.eu-central-1.amazonaws.com/sg-send-vault:latest
aws ecr get-login-password | docker login --username AWS --password-stdin <acct>.dkr.ecr.eu-central-1.amazonaws.com
docker push <acct>.dkr.ecr.eu-central-1.amazonaws.com/sg-send-vault:latest

# 2. Deploy the stack of your choice (same templates, unchanged)
aws cloudformation deploy --template-file deploy/aws/lambda.cfn.yml \
  --stack-name sg-send-lambda --capabilities CAPABILITY_IAM \
  --parameter-overrides ImageUri=<acct>.dkr.ecr.eu-central-1.amazonaws.com/sg-send-vault:latest \
                        AccessToken=<your-key>
```

Notes: the OIDC deploy role ([account setup](../new-aws-account/README.md)) is IAM = global —
no per-region step. S3 buckets are auto-named `{account}--sgraph-send-transfers--{region}`,
so regions never collide. CloudFront certs stay in us-east-1 regardless of the stack region.
