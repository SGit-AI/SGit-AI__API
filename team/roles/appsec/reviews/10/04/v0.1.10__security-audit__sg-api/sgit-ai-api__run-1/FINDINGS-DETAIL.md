# Findings detail — SGit-AI__API deploy lane (run 1)

## GitHub OIDC deploy role can rewrite its own IAM permissions (role/sgit-vaults-* matches sgit-vaults-github-deploy), so any job in the dev/main/prod environment can become AWS account admin

Fingerprint `deploy/aws/github-oidc-role.cfn.yml:DeployRole:iam-self-escalation-via-sgit-vaults-role-wildcard` · severity **high** (likelihood medium, impact critical) · confidence high

**Description.** The bootstrap template grants the GitHub OIDC deploy role iam:PutRolePolicy, iam:AttachRolePolicy, iam:CreateRole, iam:PassRole and related actions on arn:aws:iam::<account>:role/sgit-vaults-* with no Condition (no iam:PolicyARN, iam:PermissionsBoundary or iam:PassedToService), and DeployRole has no PermissionsBoundary. The role is named sgit-vaults-github-deploy, which matches that wildcard, so a session of the role can attach AdministratorAccess (or put an Action '*' Resource '*' inline policy) to itself and its next session is account admin. A second route exists even if the self-match is removed: write an admin policy onto the Lambda execution role sgit-vaults-lambda--<stage> (or a new sgit-vaults-* role), pass it to a sgit-vaults-* function via lambda:*, and run code as it. The trust policy accepts any token whose sub is repo:SGit-AI/SGit-AI__API:environment:{dev,main,prod}; the dev environment is auto-created with no protection visible in source, so anyone who can get a job to run in environment dev (a repo writer pushing to dev, dispatching, or adding a workflow on any branch that declares environment: dev) can escalate. The documented intent is that the role 'cannot touch any resource not named sgit-vaults-*'.

**Root cause.** Sid ExecutionRole scopes IAM write and pass actions only by the name prefix role/sgit-vaults-*, which also covers the deploy role itself (RoleName sgit-vaults-github-deploy). There are no conditions limiting which policies can be attached or inlined, no permissions boundary on created/modified roles or on DeployRole, and no iam:PassedToService restriction. Name scoping does not stop privilege escalation through IAM policy writes.

**Invariant.** The deploy role may only create and manage the Lambda execution role sgit-vaults-lambda--<stage>, with permissions bounded by a fixed permissions boundary. It must never be able to modify its own policies or produce a role more privileged than the documented sgit-vaults-* scope (deploy/aws/README.md:49).

### Trace

1. `.github/workflows/deploy-aws__dev.yml:3` (entrypoint, on.push.branches [dev] / workflow_dispatch): A push to dev, or a manual dispatch, by a repo writer starts the deploy workflow with stage dev.
2. `.github/workflows/deploy-aws-lambda.yml:103` (propagation, jobs.deploy.environment): The deploy job runs in the GitHub Environment named by inputs.stage (dev); environments are auto-created and reviewers are only suggested for prod. The workflow has id-token: write (line 47).
3. `.github/workflows/deploy-aws-lambda.yml:112` (propagation, jobs.deploy.steps configure-aws-credentials): The job assumes AWS_DEPLOY_ROLE_ARN with an OIDC token whose sub is repo:SGit-AI/SGit-AI__API:environment:dev.
4. `deploy/aws/github-oidc-role.cfn.yml:60` (propagation, DeployRole.AssumeRolePolicyDocument Condition StringLike sub): The trust policy accepts environment:dev, main and prod subjects for one shared role, with no ref/workflow binding.
5. `deploy/aws/github-oidc-role.cfn.yml:40` (propagation, DeployRole.Properties.RoleName): The role's own name sgit-vaults-github-deploy falls inside the sgit-vaults-* prefix; no PermissionsBoundary is set on DeployRole.
6. `deploy/aws/github-oidc-role.cfn.yml:103` (sink, DeployRole.Policies sgit-vaults-deploy Sid ExecutionRole Resource): iam:CreateRole/PutRolePolicy/AttachRolePolicy/PassRole/UpdateRole are allowed on role/sgit-vaults-* with no Condition, including the deploy role itself.

### Evidence

- `deploy/aws/github-oidc-role.cfn.yml:100`: Action list includes iam:CreateRole, iam:PassRole, iam:UpdateRole, iam:PutRolePolicy, iam:AttachRolePolicy (lines 100-102).
- `deploy/aws/github-oidc-role.cfn.yml:103`: Resource arn:aws:iam::${AWS::AccountId}:role/sgit-vaults-*, no Condition block.
- `deploy/aws/github-oidc-role.cfn.yml:40`: RoleName sgit-vaults-github-deploy matches role/sgit-vaults-*.
- `deploy/aws/github-oidc-role.cfn.yml:76`: lambda:* on function:sgit-vaults-* allows running code as any passable sgit-vaults-* role (second route).
- `deploy/aws/lambda.cfn.yml:93`: The legitimate execution role is sgit-vaults-lambda--${Stage}, so narrower scoping is feasible.
- `.github/workflows/deploy-aws-lambda.yml:133`: Stage stack deployed with CAPABILITY_NAMED_IAM under the caller's own credentials (no CloudFormation service role).
- `deploy/aws/README.md:49`: Documents that the role cannot touch any resource not named sgit-vaults-*; the policy permits account-wide escalation.

### Conditions

- (authorization_role) The attacker can run a workflow job in GitHub Environment dev, main or prod of SGit-AI/SGit-AI__API (a repo writer or compromised writer token pushing to dev or dispatching, or code running inside the deploy job). Forks and pull requests cannot obtain the environment-bound subject.
- (system_configuration) The bootstrap stack was deployed from this template with the default RoleName and AWS_DEPLOY_ROLE_ARN points at it.
- (system_configuration) No out-of-band AWS Organizations SCP, permissions boundary or explicit deny restricts iam:AttachRolePolicy/PutRolePolicy for this role (not observable from source).

### Bounded reproduction (target-neutral)
Principal: A repository writer with no AWS console access who is not meant to hold rights beyond the sgit-vaults-* deploy scope.

Input (do not run against a real account):

```
aws iam attach-role-policy --role-name sgit-vaults-github-deploy --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

Steps:
1. Render DeployRole from deploy/aws/github-oidc-role.cfn.yml with a dummy account id 111122223333; RoleName gives arn:aws:iam::111122223333:role/sgit-vaults-github-deploy.
2. Evaluate Sid ExecutionRole statically: iam:AttachRolePolicy on resource pattern arn:aws:iam::111122223333:role/sgit-vaults-* matches the role's own ARN; the statement has no Condition.
3. Confirm no other in-repo control applies: no PermissionsBoundary on DeployRole and no Deny statement.
4. Confirm a job in environment dev can obtain the role (deploy-aws-lambda.yml:103 and github-oidc-role.cfn.yml:60).
5. Do not run against any real AWS account; this is a static policy evaluation of the in-repo template.

**Observed result.** Static evaluation of the in-repo template: the identity policy allows the deploy role to call iam:AttachRolePolicy and iam:PutRolePolicy on its own ARN with any policy, including AdministratorAccess, and no in-repo boundary or deny prevents it. Out-of-band SCPs or boundaries cannot be ruled out from source. Method: source; nothing executed or promoted.

### Remediation
Stop the deploy role from writing IAM policy it, or a role it can run code as, can benefit from. Preferred: deploy the stage stack through a dedicated CloudFormation service role (aws cloudformation deploy --role-arn) and keep only iam:PassRole on that service role (iam:PassedToService cloudformation.amazonaws.com). Otherwise scope IAM writes to role/sgit-vaults-lambda--*, require iam:PermissionsBoundary on CreateRole/PutRolePolicy/AttachRolePolicy, restrict PassRole to lambda.amazonaws.com, set the boundary on ExecutionRole in lambda.cfn.yml, and explicitly deny iam:* on the deploy role's own ARN. Narrowing the prefix alone is insufficient.

`deploy/aws/github-oidc-role.cfn.yml`:
```yaml
              - Sid: ExecutionRoleWrite
                Effect: Allow
                Action: [iam:CreateRole, iam:PutRolePolicy, iam:AttachRolePolicy, iam:DetachRolePolicy, iam:DeleteRolePolicy]
                Resource: !Sub 'arn:aws:iam::${AWS::AccountId}:role/sgit-vaults-lambda--*'
                Condition:
                  StringEquals:
                    iam:PermissionsBoundary: !Sub 'arn:aws:iam::${AWS::AccountId}:policy/sgit-vaults-lambda-boundary'
              - Sid: ExecutionRolePass
                Effect: Allow
                Action: iam:PassRole
                Resource: !Sub 'arn:aws:iam::${AWS::AccountId}:role/sgit-vaults-lambda--*'
                Condition:
                  StringEquals:
                    iam:PassedToService: lambda.amazonaws.com
              - Sid: NoSelfEdits
                Effect: Deny
                Action: ['iam:*']
                Resource: !Sub 'arn:aws:iam::${AWS::AccountId}:role/sgit-vaults-github-deploy'
              - Sid: NoBoundaryRemoval
                Effect: Deny
                Action: [iam:DeleteRolePermissionsBoundary, iam:PutRolePermissionsBoundary, iam:CreatePolicyVersion, iam:SetDefaultPolicyVersion]
                Resource: '*'
```

**Regression case.** A CI policy check (cfn-guard rule or `iam simulate-custom-policy` against the rendered template) asserting implicit deny for `iam:AttachRolePolicy`/`iam:PutRolePolicy` on `role/sgit-vaults-github-deploy` and for `iam:PassRole` of any role other than `sgit-vaults-lambda--*` to `lambda.amazonaws.com`.
