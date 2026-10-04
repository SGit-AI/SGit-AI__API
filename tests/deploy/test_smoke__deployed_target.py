# ===============================================================================
# Shared smoke suite for ANY deployed SG/Send target (ADR-16 / Phase C).
#
# Parametrised over environment variables — the same suite validates Lambda,
# Fargate, EC2, Cloud Run, Heroku, or a local container:
#
#   SG_BASE_URL       required  e.g. https://xyz.lambda-url.eu-west-2.on.aws/
#   SG_ACCESS_TOKEN   optional  when set, asserts the single-key gate (ADR-12)
#
# No mocks, no patches — real HTTP against a real deployment.
# ===============================================================================

import os
import pytest
import requests

BASE_URL     = (os.environ.get('SG_BASE_URL') or '').rstrip('/')
EXPECT_UI    = (os.environ.get('SG_EXPECT_UI') or 'true').lower() != 'false'   # API-only images serve no UI at /
GATED_READS  = (os.environ.get('SG_GATED_READS') or str(EXPECT_UI)).lower() == 'true'   # the joint container gates every route; the API-only image gates writes only
ACCESS_TOKEN = os.environ.get('SG_ACCESS_TOKEN') or ''
TIMEOUT      = 30


def _headers():
    return {'x-sgraph-access-token': ACCESS_TOKEN} if ACCESS_TOKEN else {}


pytestmark = pytest.mark.skipif(not BASE_URL, reason='SG_BASE_URL not set — smoke suite targets a live deployment')


class Test_Smoke__Deployed_Target:

    def test_1__health(self):
        response = requests.get(f'{BASE_URL}/api/info/health', headers=_headers(), timeout=TIMEOUT)
        assert response.status_code == 200
        assert response.json() == {'status': 'ok'}

    def test_2__versions_endpoint(self):
        response = requests.get(f'{BASE_URL}/api/info/versions', headers=_headers(), timeout=TIMEOUT)
        assert response.status_code == 200
        assert ('sgraph_ai_app_send' in response.text) or ('sgit_vaults' in response.text)   # package name changes with the move (pack ADR-2)

    @pytest.mark.skipif(not EXPECT_UI, reason='API-only deployment — no UI at /')
    def test_3__vault_ui_root(self):
        response = requests.get(f'{BASE_URL}/', headers=_headers(), timeout=TIMEOUT)
        assert response.status_code == 200
        assert 'html' in response.headers.get('content-type', '')

    def test_4__openapi_docs(self):
        response = requests.get(f'{BASE_URL}/api/openapi.json', headers=_headers(), timeout=TIMEOUT)
        assert response.status_code == 200
        assert '/api/vault/' in response.text

    @pytest.mark.skipif(not ACCESS_TOKEN, reason='open instance — no gate to verify')
    def test_5b__write_gate__write_401_without_key(self):                         # always: a write without the key is refused
        response = requests.put(f'{BASE_URL}/api/vault/write/smoketest0001/smoke/gate.bin', data=b'x',
                                headers={'x-sgraph-vault-write-key': 'smoke-write-key'}, timeout=TIMEOUT)
        assert response.status_code == 401, f'write without the key should be 401, got {response.status_code}'

    @pytest.mark.skipif(not ACCESS_TOKEN or not GATED_READS, reason='open instance, or reads not gated on this deployment')
    def test_5__single_key_gate__all_routes_401_without_key(self):               # ADR-12: reads are gated too
        for path in ('/api/info/health', '/api/vault/read/testvault0001/somefile') + (('/en-gb/',) if EXPECT_UI else ()):
            response = requests.get(f'{BASE_URL}{path}', timeout=TIMEOUT)
            assert response.status_code == 401, f'{path} should be 401 without the key, got {response.status_code}'

    @pytest.mark.skipif(not ACCESS_TOKEN or not EXPECT_UI, reason='open instance or API-only (no login page)')
    def test_6__login_page_reachable_without_key(self):                          # the one deliberate exception
        response = requests.get(f'{BASE_URL}/auth/set-cookie-form', timeout=TIMEOUT)
        assert response.status_code == 200
        assert 'SG/SEND' in response.text

    def test_7__vault_write_read_roundtrip(self):                                # ciphertext in, same ciphertext out
        vault_id = 'smoketest0001'
        file_id  = 'smoke/probe.bin'
        payload  = b'\x00\x01smoke-cipher-probe\xff'
        write    = requests.put(f'{BASE_URL}/api/vault/write/{vault_id}/{file_id}',
                                data    = payload,
                                headers = {**_headers(), 'x-sgraph-vault-write-key': 'smoke-write-key',
                                           'content-type': 'application/octet-stream'},
                                timeout = TIMEOUT)
        assert write.status_code == 200, write.text
        read = requests.get(f'{BASE_URL}/api/vault/read/{vault_id}/{file_id}', headers=_headers(), timeout=TIMEOUT)
        assert read.status_code == 200
        assert read.content     == payload

    def test_8__cors_preflight(self):                                            # null-origin iframes must work
        response = requests.options(f'{BASE_URL}/api/info/health',
                                    headers={'Origin': 'null', 'Access-Control-Request-Method': 'GET',
                                             'Access-Control-Request-Headers': 'x-sgraph-access-token'},
                                    timeout=TIMEOUT)
        assert response.status_code in (200, 204)
        assert response.headers.get('access-control-allow-origin') in ('*', 'null')
