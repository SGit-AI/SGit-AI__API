[🏠 Deploy Hub](../../00-START-HERE.md) › **AWS EC2**

# Deploy an EC2 Appliance

**Status: 🚧 template written + lint-clean; AMI baking pipeline defined; live validation in
progress.** Template: `deploy/aws/ec2.cfn.yml`.

A dedicated instance running the container behind a **caddy auto-TLS sidecar** — set
`DomainName` and you get a real Let's Encrypt certificate with zero cert management. Data
lives on an encrypted EBS volume that becomes a **snapshot** when you delete the stack
(never silently destroyed).

```bash
aws cloudformation deploy --template-file deploy/aws/ec2.cfn.yml \
  --stack-name sg-send-box --capabilities CAPABILITY_IAM \
  --parameter-overrides DomainName=send.example.com HostedZoneId=Z... \
                        AccessToken=$(openssl rand -hex 32)
```

Key parameters: `InstanceType` (default t4g.small, arm64), `VolumeSize`, `StorageMode`
(disk|s3|memory), `AllowedCidr`, `SgSendAmiId` (use the pre-baked appliance AMI for fast
boots; empty = stock AL2023 + install at first boot). Shell access is via SSM Session
Manager — no SSH keys.
