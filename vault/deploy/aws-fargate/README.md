[🏠 Deploy Hub](../../00-START-HERE.md) › **ECS / Fargate**

# Deploy on ECS Fargate (cluster)

**Status: 🚧 template written + lint-clean; live validation in progress.** Template:
`deploy/aws/ecs-fargate.cfn.yml`.

The long-running, multi-replica pattern: N tasks behind an Application Load Balancer.
**One stack owns the entire footprint — including its own VPC** — so stack delete removes
everything. `DesiredCount > 1` requires `StorageMode=s3` (memory replicas don't share state).

```bash
aws cloudformation deploy --template-file deploy/aws/ecs-fargate.cfn.yml \
  --stack-name sg-send-cluster --capabilities CAPABILITY_IAM \
  --parameter-overrides DesiredCount=2 AccessToken=$(openssl rand -hex 32)
```

Custom domain: `DomainName` + `HostedZoneId` + `CertificateArn` (cert in the **same region**
— no us-east-1 constraint here, unlike CloudFront).
