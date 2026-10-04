# ===============================================================================
# Endpoints under test, resolved from the environment:
#
#   SG_LEGACY_URL / SG_LEGACY_TOKEN   the server the vault API is being moved FROM
#   SG_NEW_URL    / SG_NEW_TOKEN      the server it is being moved TO
#
# Either may be the literal value "inprocess": the legacy app is then booted from the
# installed `sgraph_ai_app_send` package (its own test harness, memory storage, random
# port), and the new app from `sgit_vaults` once it exists. Nothing is mocked — these
# are the real FastAPI apps behind a real HTTP port.
#
# With only one endpoint set, the invariant tests run and the parity tests skip.
# ===============================================================================

import os
import pytest
import warnings

from sgit_scenarios import Endpoint

warnings.filterwarnings('ignore')


def _inprocess_legacy():
    from sgraph_ai_app_send.lambda__user.testing.Send__User_Lambda__Test_Server import Send__User_Lambda__Http_Server
    os.environ['SEND__STORAGE_MODE'] = 'memory'
    server = Send__User_Lambda__Http_Server(); objs = server.__enter__()
    return server, Endpoint('legacy-inprocess', objs.server_url, objs.access_token)


def _inprocess_new():
    try:
        from sgit_vaults.testing.Vaults__Test_Server import Vaults__Http_Server          # lands at phase-1 step 1.3
    except ImportError:
        pytest.skip('sgit_vaults not available yet (phase-1 step 1.3)')
    os.environ['VAULTS__STORAGE_MODE'] = 'memory'
    server = Vaults__Http_Server(); objs = server.__enter__()
    return server, Endpoint('new-inprocess', objs.server_url, objs.access_token)


def _resolve(prefix, booter, name):
    url = os.environ.get(f'SG_{prefix}_URL', '')
    if not url:
        return None, None
    if url == 'inprocess':
        return booter()
    return None, Endpoint(name, url, os.environ.get(f'SG_{prefix}_TOKEN', ''))


@pytest.fixture(scope='session')
def legacy():
    server, ep = _resolve('LEGACY', _inprocess_legacy, 'legacy')
    if ep is None: pytest.skip('SG_LEGACY_URL not set')
    yield ep
    if server: server.__exit__(None, None, None)


@pytest.fixture(scope='session')
def new():
    server, ep = _resolve('NEW', _inprocess_new, 'new')
    if ep is None: pytest.skip('SG_NEW_URL not set')
    yield ep
    if server: server.__exit__(None, None, None)
