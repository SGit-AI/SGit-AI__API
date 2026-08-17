import shutil
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib     import Path
from unittest    import TestCase

from sgit_ai.crypto.Vault__Crypto import Vault__Crypto

# The static-vault conformance suite (see team/comms/changelog/08/17 and vault/README.md).
#
# The product claim under test: the server is storage which reads nothing — every read is
# a GET of a path computed from a key, so a host that can only serve files is a complete
# read endpoint. Anything that breaks against a plain static file server is a hidden
# dependency on server behaviour. Exactly three things are expected to break: batch reads
# (the real gap), writes and authentication (both intended for a published vault).
#
# The "server" here is a real static file host (stdlib ThreadingHTTPServer serving bytes
# off disk) — not a mock of the SG/Send API. It serves the repository's reference vault
# (vault/.sg_vault/bare/) at the exact paths the live API serves:
#     GET /api/vault/read/<vault-id>/bare/<...>

REPO_ROOT   = Path(__file__).resolve().parents[3]
VAULT_DIR   = REPO_ROOT / 'vault'
BARE_DIR    = VAULT_DIR / '.sg_vault' / 'bare'

VAULT_ID    = 'ivpijuvg'                                                                # the reference vault (see vault/README.md)
READ_KEY    = 'c28b118c9a7a101910efa24a3a49b6cc6dbec8e8dcdc8fea671e89cecb0ab817'        # published deliberately — read-only capability
READ_PREFIX = f'/api/vault/read/{VAULT_ID}/'


class Static_Vault_Handler(BaseHTTPRequestHandler):                                     # a static host: GETs of files, nothing else

    requests_seen = None                                                                # set per test-class to a list of (method, path, status)

    def _record(self, status):
        if Static_Vault_Handler.requests_seen is not None:
            Static_Vault_Handler.requests_seen.append((self.command, self.path, status))

    def do_GET(self):
        path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        if path.startswith(READ_PREFIX):
            rel    = path[len(READ_PREFIX):]                                            # e.g. bare/refs/ref-pid-muw-...
            target = (VAULT_DIR / '.sg_vault' / rel).resolve()
            if target.is_file() and target.is_relative_to(BARE_DIR.resolve()):
                data = target.read_bytes()
                self._record(200)
                self.send_response(200)
                self.send_header('Content-Type'  , 'application/octet-stream')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
        self._record(404)
        self.send_response(404)
        self.end_headers()

    def _refuse(self):                                                                  # a static host accepts no writes and no RPC
        self._record(405)
        self.send_response(405)
        self.end_headers()

    do_POST   = _refuse
    do_PUT    = _refuse
    do_DELETE = _refuse

    def log_message(self, format, *args):                                               # keep pytest output clean
        pass


class test_Static_Vault_Read_Path(TestCase):

    @classmethod
    def setUpClass(cls):
        assert BARE_DIR.is_dir(), f'reference vault store missing: {BARE_DIR}'
        Static_Vault_Handler.requests_seen = []
        cls.server   = ThreadingHTTPServer(('127.0.0.1', 0), Static_Vault_Handler)
        cls.thread   = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f'http://127.0.0.1:{cls.server.server_address[1]}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        Static_Vault_Handler.requests_seen = None

    # -- the claim that holds: every byte a reader needs is a plain GET ---------------

    def test__every_committed_object_is_served_byte_identical(self):                    # storage layer: static host == live read endpoint
        files = sorted(p for p in BARE_DIR.rglob('*') if p.is_file())
        assert len(files) >= 5                                                          # refs + index + commit + tree + blobs at minimum
        for file in files:
            rel  = file.relative_to(BARE_DIR).as_posix()
            url  = f'{self.base_url}{READ_PREFIX}bare/{rel}'
            with urllib.request.urlopen(url) as response:
                assert response.status == 200        , f'not fetchable statically: {rel}'
                assert response.read() == file.read_bytes(), f'byte drift: {rel}'

    def test__credential_tier_is_not_in_the_git_index(self):                            # the leak guard: local/ (vault key, token) must never be committed
        result  = subprocess.run(['git', 'ls-files', 'vault/'],
                                 cwd=REPO_ROOT, capture_output=True, text=True)
        if result.returncode != 0:                                                      # not a git checkout (e.g. sdist) — nothing to guard
            self.skipTest('not running inside a git checkout')
        tracked = result.stdout.splitlines()
        assert any(line.startswith('vault/.sg_vault/bare/') for line in tracked)        # the ciphertext mirror IS committed
        for line in tracked:
            assert not line.startswith('vault/.sg_vault/local/')                        # the plaintext credential tier is NOT
            assert not line.startswith('vault/.sg_vault/work/' )

    # -- the two intended breaks: writes and authentication ---------------------------

    def test__write_attempt_is_refused(self):                                           # a published vault is a read-only snapshot
        ref      = next(BARE_DIR.glob('refs/*'))
        rel      = ref.relative_to(BARE_DIR).as_posix()
        before   = ref.read_bytes()
        request  = urllib.request.Request(f'{self.base_url}{READ_PREFIX}bare/{rel}',
                                          data=b'overwrite-attempt', method='PUT')
        try:
            urllib.request.urlopen(request)
            status = 200
        except urllib.error.HTTPError as error:
            status = error.code
        assert status >= 400                                                            # refused
        assert ref.read_bytes() == before                                               # and nothing changed

    # -- the claim that holds: names are computed from the key, never listed ----------

    def test__named_ref_is_derived_from_the_read_key_alone(self):                       # no discovery call exists — the first request's
        crypto = Vault__Crypto()                                                        # filename is an HMAC of the (published) read key
        ref_id = 'ref-pid-muw-' + crypto.derive_ref_file_id(bytes.fromhex(READ_KEY), VAULT_ID)
        assert (BARE_DIR / 'refs' / ref_id).is_file()                                   # the derived name exists in the committed store…
        url    = f'{self.base_url}{READ_PREFIX}bare/refs/{ref_id}'
        with urllib.request.urlopen(url) as response:
            assert response.status == 200                                               # …and one plain GET fetches it statically

    # -- the one real gap, pinned: the CLI clone depends on the batch endpoint --------

    def test__cli_clone_stops_at_batch(self):
        # GOOD FAILURE ahead: when the sgit CLI ships static fan-out (batch reads
        # falling back to parallel GETs, as the browser transport already does), this
        # test SHOULD break — replace it with an assertion that the clone succeeds and
        # the checked-out files match vault/'s working tree.
        sgit = shutil.which('sgit')
        assert sgit is not None, 'sgit CLI not installed — it is in requirements-test.txt'

        Static_Vault_Handler.requests_seen.clear()
        clone_dir = Path(self.enterContext(_tempdir())) / 'static-clone'
        result    = subprocess.run([sgit, 'clone',
                                    '--base-url', self.base_url,
                                    '--read-key', READ_KEY,
                                    VAULT_ID, str(clone_dir)],
                                   capture_output=True, text=True, timeout=120)
        seen      = list(Static_Vault_Handler.requests_seen)

        batch_posts = [r for r in seen if r[0] == 'POST' and f'/api/vault/batch/{VAULT_ID}' in r[1]]
        assert batch_posts != []                                                        # the clone reached for the batch endpoint,
        assert result.returncode != 0                                                   # which a static host does not have: the pinned gap


def _tempdir():
    import tempfile
    return tempfile.TemporaryDirectory()
