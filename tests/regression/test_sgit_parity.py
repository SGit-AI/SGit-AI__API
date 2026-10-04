# ===============================================================================
# The parity gate.
#
#   invariants  — what must hold on ANY vault server (run with one endpoint)
#   parity      — the SAME scenario on legacy and new must yield the SAME observation
#
# "Same" is structural: status codes, response shapes, cache headers, bytes round-tripped,
# clone trees equal — never ids, dates or ciphertext. A difference here is a behaviour
# change, which the Villager pack forbids; find it before deploying.
# ===============================================================================

import json
import pytest

from sgit_scenarios import SCENARIOS, observe


# --- invariants: run against legacy if present, else new -------------------------------

@pytest.fixture(scope='session')
def any_endpoint(request):
    for name in ('legacy', 'new'):
        try:
            return request.getfixturevalue(name)
        except pytest.skip.Exception:
            continue
    pytest.skip('no endpoint configured (SG_LEGACY_URL or SG_NEW_URL)')


class Test_Invariants:

    def test__roundtrip(self, any_endpoint):
        obs = observe(any_endpoint, 'roundtrip')
        assert obs['full_clone_matches']     is True
        assert obs['readonly_clone_matches'] is True
        assert obs['named_ref_get']          == 200                  # the read contract: a plain GET
        assert obs['vault_health'][0]        == 200
        assert set(obs['bare_layout']) >= {'data', 'refs'}

    def test__second_push_and_pull(self, any_endpoint):
        obs = observe(any_endpoint, 'second_push_and_pull')
        assert obs['clone_was_v1']   is True
        assert obs['pull_brought_v2'] is True

    def test__api_contract(self, any_endpoint):
        obs = observe(any_endpoint, 'api_contract')
        assert obs['openapi'] == 200 and obs['docs'] == 200
        assert obs['health'] == (200, {'status': 'ok'})
        paths = obs['vault_and_info_paths']
        for must in ('/api/vault/read/{vault_id}/{file_id}', '/api/vault/write/{vault_id}/{file_id}',
                     '/api/vault/batch/{vault_id}', '/api/vault/append/write/{vault_id}', '/api/info/health'):
            assert must in paths, f'missing from contract: {must}'

    def test__pointer_api(self, any_endpoint):
        obs = observe(any_endpoint, 'pointer_api')
        assert obs['write'][0] == 200
        assert obs['read'] == (200, True, 'public, max-age=31536000, immutable')   # -imm- ids cache forever
        assert obs['read_missing'] == 404
        assert obs['batch_read_noauth'][0] == 200                                    # read-only batch needs no auth
        assert obs['zip'] == (200, True)
        assert obs['write_wrong_key'] == 403
        assert obs['write_no_token'] in (401, 200)                                   # 200 only on an open instance
        assert obs['destroy'][0] == 200 and obs['health_after_destroy'] == 404

    def test__append_lane(self, any_endpoint):
        obs = observe(any_endpoint, 'append_lane')
        assert obs['configure'][0] == 200
        assert obs['write_blind'] == (200, {'ok': True})                             # blind: no id, no count
        assert obs['write_bad_token'] == 403
        assert obs['list'][0] == 200 and obs['list'][2] == 1
        assert obs['mark_processed'][0] == 200
        assert obs['list_wrong_enum'] == 403
        assert obs['purge'][0] == 200


# --- parity: legacy vs new, scenario by scenario ---------------------------------------

@pytest.mark.parametrize('scenario', sorted(SCENARIOS))
def test__parity(legacy, new, scenario):
    a = observe(legacy, scenario)
    b = observe(new,    scenario)
    assert a == b, ('BEHAVIOUR DIFFERS between legacy and new for scenario '
                    f'{scenario!r}:\n--- legacy ---\n{json.dumps(a, indent=1, default=str)}\n--- new ---\n{json.dumps(b, indent=1, default=str)}')
