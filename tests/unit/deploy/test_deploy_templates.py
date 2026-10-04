# Policy tests for the AWS deploy lane. No AWS, no mocks: the templates and workflows are parsed
# as data and the invariants the 4 Oct 2026 security audit asked for are pinned here, so the
# confirmed finding (the deploy role could rewrite its own IAM policy and become account admin)
# and the three leads next to it cannot come back without a red test.
import re
from pathlib import Path
from unittest import TestCase

import yaml

REPO_ROOT      = Path(__file__).resolve().parents[3]
OIDC_TEMPLATE  = REPO_ROOT / 'deploy/aws/github-oidc-role.cfn.yml'
STACK_TEMPLATE = REPO_ROOT / 'deploy/aws/lambda.cfn.yml'
WORKFLOWS      = sorted((REPO_ROOT / '.github/workflows').glob('deploy-aws*.yml'))
BOUNDARY_ARN   = 'arn:aws:iam::${AWS::AccountId}:policy/sgit-vaults-lambda-boundary'


class CfnLoader(yaml.SafeLoader):                                               # CloudFormation short-form tags, kept as data
    pass

def _tag(loader, suffix, node):
    if isinstance(node, yaml.ScalarNode):   return {f'Fn::{suffix}': loader.construct_scalar(node)}
    if isinstance(node, yaml.SequenceNode): return {f'Fn::{suffix}': loader.construct_sequence(node)}
    return {f'Fn::{suffix}': loader.construct_mapping(node)}

for _name in ['Sub', 'Ref', 'GetAtt', 'If', 'Equals', 'And', 'Not', 'Or', 'Join', 'Select', 'Split', 'Condition', 'FindInMap']:
    CfnLoader.add_constructor(f'!{_name}', (lambda n: lambda loader, node: _tag(loader, n, node))(_name))

def load_cfn(path: Path) -> dict:
    return yaml.load(path.read_text(), Loader=CfnLoader)

def as_text(value) -> str:                                                      # flatten !Sub / !Ref / lists into one searchable string
    if isinstance(value, dict):  return ' '.join(f'{k} {as_text(v)}' for k, v in value.items())
    if isinstance(value, list):  return ' '.join(as_text(v) for v in value)
    return str(value)

def as_list(value) -> list:
    return value if isinstance(value, list) else [value]

def statements(role: dict) -> list:
    return [s for p in role['Properties']['Policies'] for s in p['PolicyDocument']['Statement']]


class Test_Deploy_Role_Template(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.template = load_cfn(OIDC_TEMPLATE)
        cls.role     = cls.template['Resources']['DeployRole']
        cls.allows   = [s for s in statements(cls.role) if s['Effect'] == 'Allow']
        cls.denies   = [s for s in statements(cls.role) if s['Effect'] == 'Deny']
        cls.iam_allows = [s for s in cls.allows if any(a.startswith('iam:') for a in as_list(s['Action']))]

    def test__one_role_per_stage__name_and_trust_carry_the_stage(self):
        name  = as_text(self.role['Properties']['RoleName'])
        assert 'sgit-vaults-github-deploy--${Stage}' in name
        trust = self.role['Properties']['AssumeRolePolicyDocument']['Statement'][0]['Condition']
        subs  = as_list(trust['StringEquals']['token.actions.githubusercontent.com:sub'])
        assert len(subs) == 1,                            'exactly one OIDC subject: this stage\'s GitHub Environment'
        assert 'environment:${Stage}' in as_text(subs[0]), subs
        assert 'StringLike' not in trust,                 'no wildcard subjects'

    def test__the_role_can_never_touch_a_deploy_role__itself_included(self):
        # the confirmed finding: role/sgit-vaults-* matched the deploy role's own name
        for s in self.iam_allows:
            for resource in as_list(s['Resource']):
                text = as_text(resource)
                assert 'role/sgit-vaults-lambda--${Stage}' in text, f'IAM allow must be the stage execution role only, got: {text}'
                assert 'github-deploy' not in text
        deny = [s for s in self.denies if 'iam:*' in as_list(s['Action'])]
        assert deny, 'an explicit Deny iam:* on role/sgit-vaults-github-deploy--* is required'
        assert 'role/sgit-vaults-github-deploy--*' in as_text(deny[0]['Resource'])

    def test__creating_or_editing_the_execution_role_requires_the_boundary(self):
        writers = {'iam:CreateRole', 'iam:PutRolePolicy', 'iam:AttachRolePolicy', 'iam:PutRolePermissionsBoundary'}
        seen    = set()
        for s in self.iam_allows:
            actions = set(as_list(s['Action']))
            if actions & writers:
                assert actions <= writers,  f'boundary-conditioned statement mixes in other actions: {actions}'
                cond = s.get('Condition', {}).get('StringEquals', {})
                assert as_text(cond.get('iam:PermissionsBoundary')) .endswith(BOUNDARY_ARN.split('::')[-1]), s
                seen |= actions
        assert seen == writers, f'every policy-writing action must be boundary-conditioned; missing {writers - seen}'

    def test__pass_role_only_to_lambda(self):
        passes = [s for s in self.iam_allows if 'iam:PassRole' in as_list(s['Action'])]
        assert passes, 'the deploy role must be able to pass the execution role to Lambda'
        for s in passes:
            assert as_list(s['Action']) == ['iam:PassRole'],         'PassRole stands alone so its condition cannot be bypassed'
            assert s['Condition']['StringEquals']['iam:PassedToService'] == 'lambda.amazonaws.com'

    def test__the_boundary_cannot_be_weakened_by_the_role(self):
        actions = {a for s in self.denies for a in as_list(s['Action'])}
        for must_deny in ['iam:DeleteRolePermissionsBoundary', 'iam:CreatePolicyVersion', 'iam:SetDefaultPolicyVersion', 'iam:DeletePolicy', 'iam:CreatePolicy']:
            assert must_deny in actions, must_deny

    def test__stage_scoped_resources_and_no_object_access(self):
        for s in self.allows:
            if s['Sid'] in ('Stack', 'LambdaAndLogs', 'Bucket', 'ExecutionRoleWrite', 'ExecutionRoleManage', 'ExecutionRolePass'):
                assert '${Stage}' in as_text(s['Resource']), f'{s["Sid"]} must be scoped to the stage'
        bucket = next(s for s in self.allows if s['Sid'] == 'Bucket')
        for action in as_list(bucket['Action']):
            assert not action.startswith('s3:*') and not action.endswith('Object') and 'Put*' not in action, action
            assert action not in ('s3:PutBucketPolicy', 's3:PutBucketAcl', 's3:DeleteBucketPolicy'), action
        assert '/*' not in as_text(bucket['Resource']),  'no object-level resource'

    def test__the_boundary_policy_is_the_ceiling_the_stack_template_uses(self):
        boundary = self.template['Resources']['LambdaBoundary']
        assert boundary['Properties']['ManagedPolicyName'] == 'sgit-vaults-lambda-boundary'
        for s in boundary['Properties']['PolicyDocument']['Statement']:
            assert s['Effect'] == 'Allow'
            assert all(a.startswith(('logs:', 's3:')) for a in as_list(s['Action'])), s
            assert '*' != as_text(s['Resource']).strip(), 'the ceiling is name-scoped too'


class Test_Stack_Template(TestCase):

    def test__execution_role_carries_the_boundary(self):
        template = load_cfn(STACK_TEMPLATE)
        role     = template['Resources']['ExecutionRole']['Properties']
        assert as_text(role['PermissionsBoundary']).endswith('policy/sgit-vaults-lambda-boundary')
        assert 'sgit-vaults-lambda--${Stage}' in as_text(role['RoleName'])


class Test_Deploy_Workflows(TestCase):

    def test__no_input_or_secret_is_interpolated_into_shell_text(self):
        # expression injection: `${{ inputs.x }}` inside run: becomes shell text; values go through env: instead
        for path in WORKFLOWS:
            doc = yaml.safe_load(path.read_text())
            for job_name, job in doc['jobs'].items():
                for step in job.get('steps', []) or []:
                    run = step.get('run', '')
                    assert not re.search(r'\$\{\{\s*(inputs|secrets|github\.event)\.', run), f'{path.name}:{job_name}: {run}'

    def test__only_the_environment_bound_job_can_mint_an_oidc_token(self):
        base = yaml.safe_load((REPO_ROOT / '.github/workflows/deploy-aws-lambda.yml').read_text())
        assert base['permissions'].get('id-token') != 'write',           'id-token: write must not be workflow-wide'
        for job_name, job in base['jobs'].items():
            uses_aws = any('configure-aws-credentials' in (s.get('uses') or '') for s in job.get('steps', []) or [])
            if uses_aws or (job.get('permissions') or {}).get('id-token') == 'write':
                assert job.get('environment'), f'{job_name} holds AWS credentials and must run inside the stage Environment'
                assert job['permissions']['id-token'] == 'write'

    def test__callers_inherit_environment_secrets_and_never_default_to_open(self):
        for path in WORKFLOWS:
            if path.name == 'deploy-aws-lambda.yml':
                continue
            doc = yaml.safe_load(path.read_text())
            (job,) = doc['jobs'].values()
            assert job['secrets'] == 'inherit', path.name
            assert 'open_instance' in job['with'], path.name
            inputs = (doc.get(True) or doc.get('on'))['workflow_dispatch']['inputs']
            assert inputs['open_instance']['default'] is False, path.name

    def test__an_empty_token_fails_closed_unless_open_instance_is_explicit(self):
        base = (REPO_ROOT / '.github/workflows/deploy-aws-lambda.yml').read_text()
        assert 'if [ -z "$ACCESS_TOKEN" ] && [ "$OPEN_INSTANCE" != "true" ]' in base
        assert 'exit 1' in base.split('Refusing to deploy an OPEN instance')[1][:120]
