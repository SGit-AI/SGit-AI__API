# ===============================================================================
# sgit parity scenarios
#
# Each scenario drives ONE vault server (base_url + access token) the way a real
# client does — the sgit CLI as a subprocess, plus raw HTTP against the vault API
# with keys derived exactly as the CLI derives them — and returns a normalised
# OBSERVATION: a dict with no per-run identifiers (vault ids, object ids, dates,
# ciphertext) so that two servers given the same inputs must produce the same
# dict. The parity test runs every scenario against the legacy server and the
# new server and asserts the observations are equal; the invariant tests run
# them against a single server and assert what must always hold.
#
# No mocks. The servers are real (in-process via their test harness, or remote).
# ===============================================================================

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import requests
from sgit_ai.crypto.Vault__Crypto import Vault__Crypto

HEADER__ACCESS_TOKEN = 'x-sgraph-access-token'
HEADER__WRITE_KEY    = 'x-sgraph-vault-write-key'
HEADER__ENUM_KEY     = 'x-sgraph-vault-enum-key'
TIMEOUT              = 60

VAULT_FAMILY_PREFIXES = ('/api/vault', '/api/info')               # the contract under parity


class Endpoint:                                                    # one server under test
    def __init__(self, name, base_url, token):
        self.name     = name
        self.base_url = base_url.rstrip('/')
        self.token    = token

    def headers(self, **extra):
        h = {HEADER__ACCESS_TOKEN: self.token} if self.token else {}
        h.update(extra)
        return h


class Sgit:                                                        # thin driver over the CLI, one working dir per vault
    def __init__(self, endpoint: Endpoint, workdir: Path):
        self.endpoint = endpoint
        self.workdir  = Path(workdir)
        self.sgit     = shutil.which('sgit')
        assert self.sgit, 'sgit CLI not installed (pip install sgit-ai)'

    def run(self, *args, cwd=None, check=True):
        cmd = [self.sgit, '--base-url', self.endpoint.base_url]
        if self.endpoint.token:
            cmd += ['--token', self.endpoint.token]
        cmd += list(args)
        result = subprocess.run(cmd, cwd=str(cwd or self.workdir), capture_output=True, text=True, timeout=TIMEOUT * 3)
        if check and result.returncode != 0:
            raise AssertionError(f'sgit {" ".join(args)} failed ({result.returncode}):\n{result.stdout}\n{result.stderr}')
        return result

    def init(self):
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.run('init', '--existing')
        return self.keys()

    def keys(self):
        vault_key = (self.workdir / '.sg_vault' / 'local' / 'vault_key').read_text().strip()
        return Vault__Crypto().derive_keys_from_vault_key(vault_key) | {'vault_key': vault_key}

    def commit(self, message):  self.run('commit', '-m', message)
    def push(self):             self.run('push')
    def pull(self, cwd=None):   self.run('pull', cwd=cwd)

    def clone(self, vault_key, into: Path, read_key_hex=None, vault_id=None):
        into = Path(into)
        if read_key_hex:
            self.run('clone', '--read-key', read_key_hex, vault_id, str(into), cwd=into.parent)
        else:
            self.run('clone', vault_key, str(into), cwd=into.parent)
        return into


# --- helpers ---------------------------------------------------------------------

def tree_digest(root: Path) -> dict:                              # {relative path: sha256} of the plaintext working tree
    out = {}
    for p in sorted(Path(root).rglob('*')):
        if p.is_file() and '.sg_vault' not in p.parts:
            out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out

def write_fixture(root: Path, version: int):
    root.mkdir(parents=True, exist_ok=True)
    (root / 'README.md').write_text(f'# parity fixture v{version}\n')
    (root / 'data').mkdir(exist_ok=True)
    (root / 'data' / 'numbers.json').write_text(json.dumps({'version': version, 'values': list(range(version * 10))}))
    (root / 'data' / 'blob.bin').write_bytes(bytes(range(256)) * (4 * version))
    if version >= 2:
        (root / 'notes.txt').write_text('added in v2\n')

def shape(obj):                                                    # structural shape of a JSON body: keys + value types, no values
    if isinstance(obj, dict):  return {k: shape(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):  return [shape(obj[0])] if obj else []
    return type(obj).__name__

def http(endpoint: Endpoint, method, path, **kw):
    kw.setdefault('timeout', TIMEOUT)
    r = requests.request(method, endpoint.base_url + path, **kw)
    body = None
    try:    body = r.json()
    except Exception: body = None
    return r.status_code, body, r.content


# --- scenarios -------------------------------------------------------------------
# Each takes an Endpoint and a scratch dir, returns a normalised observation dict.

def scenario__roundtrip(endpoint: Endpoint, scratch: Path) -> dict:
    """init → commit v1 → push → clone with the vault key → clone read-only with the read key.
    Both clones must reproduce the working tree exactly; the named ref must be a plain GET."""
    work = Path(scratch) / 'work'; write_fixture(work, 1)
    cli  = Sgit(endpoint, work); keys = cli.init(); cli.commit('v1'); cli.push()
    full = cli.clone(keys['vault_key'], Path(scratch) / 'clone-full')
    ro   = cli.clone(None, Path(scratch) / 'clone-ro', read_key_hex=keys['read_key_bytes'].hex(), vault_id=keys['vault_id'])
    ref_id = 'ref-pid-muw-' + Vault__Crypto().derive_ref_file_id(keys['read_key_bytes'], keys['vault_id'])
    ref_status, _, _ = http(endpoint, 'GET', f'/api/vault/read/{keys["vault_id"]}/bare/refs/{ref_id}')
    health, hbody, _ = http(endpoint, 'GET', f'/api/vault/health/{keys["vault_id"]}')
    return {
        'tree_after_push'       : tree_digest(work),
        'full_clone_matches'    : tree_digest(full) == tree_digest(work),
        'readonly_clone_matches': tree_digest(ro)   == tree_digest(work),
        'named_ref_get'         : ref_status,
        'vault_health'          : (health, shape(hbody)),
        'bare_layout'           : sorted({p.parts[0] for p in (work / '.sg_vault' / 'bare').rglob('*') if p.is_file() for p in [p.relative_to(work / '.sg_vault' / 'bare')]}),
        '_vault_id': keys['vault_id'], '_keys': keys,               # underscore keys are stripped before comparison
    }


def scenario__second_push_and_pull(endpoint: Endpoint, scratch: Path) -> dict:
    """v1 pushed; a second workspace clones; v2 pushed from the first; the clone pulls and must match v2."""
    work = Path(scratch) / 'work'; write_fixture(work, 1)
    cli  = Sgit(endpoint, work); keys = cli.init(); cli.commit('v1'); cli.push()
    other = cli.clone(keys['vault_key'], Path(scratch) / 'other')
    before = tree_digest(other)
    write_fixture(work, 2); cli.commit('v2'); cli.push()
    cli.pull(cwd=other)
    return {
        'clone_was_v1'      : before == tree_digest(Path(scratch) / 'work') if False else 'README.md' in before and 'notes.txt' not in before,
        'pull_brought_v2'   : tree_digest(other) == tree_digest(work),
        'history_count'     : len([l for l in cli.run('history', 'log', cwd=work, check=False).stdout.splitlines() if 'v1' in l or 'v2' in l]) if True else None,
    }


def scenario__api_contract(endpoint: Endpoint, scratch: Path) -> dict:
    """The vault + info families of the OpenAPI document, path for path, method for method; and docs served."""
    status, spec, _ = http(endpoint, 'GET', '/api/openapi.json')
    paths = {p: sorted(m.upper() for m in v) for p, v in (spec or {}).get('paths', {}).items() if p.startswith(VAULT_FAMILY_PREFIXES)}
    docs, _, _   = http(endpoint, 'GET', '/api/docs')
    health, hb, _ = http(endpoint, 'GET', '/api/info/health')
    return {'openapi': status, 'vault_and_info_paths': paths, 'docs': docs, 'health': (health, hb)}


def scenario__pointer_api(endpoint: Endpoint, scratch: Path) -> dict:
    """Raw pointer API with CLI-derived keys: write, read (bytes + cache headers), batch read, list, zip, delete, destroy."""
    work = Path(scratch) / 'work'; write_fixture(work, 1)
    cli = Sgit(endpoint, work); keys = cli.init(); cli.commit('v1'); cli.push()
    vid, wk = keys['vault_id'], keys['write_key']
    payload = b'\x00parity-probe\xff' * 16
    obs = {}
    s, b, _ = http(endpoint, 'PUT', f'/api/vault/write/{vid}/probe/obj-cas-imm-parity01', data=payload, headers=endpoint.headers(**{HEADER__WRITE_KEY: wk}))
    obs['write']            = (s, shape(b))
    s, _, raw = http(endpoint, 'GET', f'/api/vault/read/{vid}/probe/obj-cas-imm-parity01')
    r = requests.get(endpoint.base_url + f'/api/vault/read/{vid}/probe/obj-cas-imm-parity01', timeout=TIMEOUT)
    obs['read']             = (s, raw == payload, r.headers.get('cache-control'))
    r2 = requests.get(endpoint.base_url + f'/api/vault/read/{vid}/probe/mutable-ref', timeout=TIMEOUT)
    obs['read_missing']     = r2.status_code
    s, b, _ = http(endpoint, 'GET', f'/api/vault/read-base64/{vid}/probe/obj-cas-imm-parity01')
    obs['read_base64']      = (s, shape(b))
    s, b, _ = http(endpoint, 'POST', f'/api/vault/batch/{vid}', json={'operations': [{'op': 'read', 'file_id': 'probe/obj-cas-imm-parity01'}, {'op': 'read', 'file_id': 'probe/nope'}]})
    obs['batch_read_noauth']= (s, shape(b))
    s, b, _ = http(endpoint, 'GET', f'/api/vault/list/{vid}', params={'prefix': 'probe/'})
    obs['list']             = (s, shape(b), len((b or {}).get('files', [])) if isinstance(b, dict) else None)
    s, _, raw = http(endpoint, 'GET', f'/api/vault/zip/{vid}', headers=endpoint.headers(**{HEADER__WRITE_KEY: wk}))
    obs['zip']              = (s, raw[:2] == b'PK')
    s, b, _ = http(endpoint, 'PUT', f'/api/vault/write/{vid}/probe/x', data=b'x', headers=endpoint.headers(**{HEADER__WRITE_KEY: 'wrong'}))
    obs['write_wrong_key']  = s
    s, b, _ = http(endpoint, 'PUT', f'/api/vault/write/{vid}/probe/x', data=b'x', headers={HEADER__WRITE_KEY: wk})
    obs['write_no_token']   = s
    s, b, _ = http(endpoint, 'DELETE', f'/api/vault/delete/{vid}/probe/obj-cas-imm-parity01', headers=endpoint.headers(**{HEADER__WRITE_KEY: wk}))
    obs['delete']           = (s, shape(b))
    s, b, _ = http(endpoint, 'DELETE', f'/api/vault/destroy/{vid}', json={'vault_id': vid, 'purge': True}, headers=endpoint.headers(**{HEADER__WRITE_KEY: wk}))
    obs['destroy']          = (s, shape(b))
    s, _, _ = http(endpoint, 'GET', f'/api/vault/health/{vid}')
    obs['health_after_destroy'] = s
    return obs


def scenario__append_lane(endpoint: Endpoint, scratch: Path) -> dict:
    """configure (write key) → blind write (append token) → list/fetch/mark-processed (enum key) → purge (write key)."""
    work = Path(scratch) / 'work'; write_fixture(work, 1)
    cli = Sgit(endpoint, work); keys = cli.init(); cli.commit('v1'); cli.push()
    vid, wk = keys['vault_id'], keys['write_key']
    token    = hashlib.sha256(b'parity-append-token').hexdigest()
    enum_key = hashlib.sha256(b'parity-enum-key').hexdigest()
    obs = {}
    s, b, _ = http(endpoint, 'POST', f'/api/vault/append/configure/{vid}', json={'append_anchors': [hashlib.sha256(token.encode()).hexdigest()], 'enum_key_hash': hashlib.sha256(enum_key.encode()).hexdigest()}, headers=endpoint.headers(**{HEADER__WRITE_KEY: wk}))
    obs['configure']        = (s, shape(b))
    import base64
    s, b, _ = http(endpoint, 'POST', f'/api/vault/append/write/{vid}', json={'append_token': token, 'payload': base64.b64encode(b'hello-lane').decode()})
    obs['write_blind']      = (s, b)
    s, b, _ = http(endpoint, 'POST', f'/api/vault/append/write/{vid}', json={'append_token': 'f' * 64, 'payload': base64.b64encode(b'x').decode()})
    obs['write_bad_token']  = s
    s, b, _ = http(endpoint, 'POST', f'/api/vault/append/list/{vid}', json={'inbox': token}, headers={HEADER__ENUM_KEY: enum_key})
    obs['list']             = (s, shape(b), len((b or {}).get('entries', [])) if isinstance(b, dict) else None)
    entries = (b or {}).get('entries', []) if isinstance(b, dict) else []
    ids = [e.get('file_id') for e in entries if isinstance(e, dict)]
    s, b, _ = http(endpoint, 'POST', f'/api/vault/append/fetch/{vid}', json={'inbox': token, 'file_ids': ids}, headers={HEADER__ENUM_KEY: enum_key})
    obs['fetch']            = (s, shape(b))
    s, b, _ = http(endpoint, 'POST', f'/api/vault/append/mark-processed/{vid}', json={'inbox': token, 'file_ids': ids}, headers={HEADER__ENUM_KEY: enum_key})
    obs['mark_processed']   = (s, shape(b))
    s, b, _ = http(endpoint, 'POST', f'/api/vault/append/list/{vid}', json={'inbox': token}, headers={HEADER__ENUM_KEY: 'wrong'})
    obs['list_wrong_enum']  = s
    s, b, _ = http(endpoint, 'POST', f'/api/vault/append/purge/{vid}', json={'inbox': token, 'folder': 'processed'}, headers=endpoint.headers(**{HEADER__WRITE_KEY: wk}))
    obs['purge']            = (s, shape(b))
    return obs


SCENARIOS = {
    'roundtrip'            : scenario__roundtrip,
    'second_push_and_pull' : scenario__second_push_and_pull,
    'api_contract'         : scenario__api_contract,
    'pointer_api'          : scenario__pointer_api,
    'append_lane'          : scenario__append_lane,
}


def observe(endpoint: Endpoint, scenario_name: str) -> dict:
    scratch = Path(tempfile.mkdtemp(prefix=f'sgit-parity-{scenario_name}-{endpoint.name}-'))
    try:
        obs = SCENARIOS[scenario_name](endpoint, scratch)
        return {k: v for k, v in obs.items() if not k.startswith('_')}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
