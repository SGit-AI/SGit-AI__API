/* SgitStaticReader — a read-only sgit vault reader over plain byte fetches.
 *
 * Mirrors sgit_ai/crypto/Vault__Crypto.py exactly:
 *   ref file id  = 'ref-pid-muw-' + hex(HMAC-SHA256(read_key, 'sg-vault-v1:file-id:ref:'+vault_id))[:12]
 *   objects      = AES-256-GCM, stored as iv(12) || ciphertext(+tag)
 *   metadata     = base64( iv || ciphertext ) of UTF-8 plaintext
 *
 * Runs in the browser (WebCrypto) and in Node >= 19 (global crypto) so the same
 * file is testable in CI against the committed store. The byte source is
 * injected: fetchBytes(relPath) -> Uint8Array, where relPath is relative to the
 * vault's bare/ tree (e.g. 'refs/ref-pid-muw-…', 'data/obj-cas-imm-…').
 */
'use strict';

const SgitStaticReader = (() => {
  const te = new TextEncoder();
  const td = new TextDecoder();

  const hexBytes = hexStr => Uint8Array.from(hexStr.match(/.{2}/g).map(b => parseInt(b, 16)));
  const toHex    = bytes  => [...bytes].map(b => b.toString(16).padStart(2, '0')).join('');
  const b64Bytes = b64    => Uint8Array.from(atob(b64), c => c.charCodeAt(0));

  async function hmacSha256(keyBytes, message) {
    const key = await crypto.subtle.importKey('raw', keyBytes, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
    return new Uint8Array(await crypto.subtle.sign('HMAC', key, te.encode(message)));
  }

  async function deriveRefFileId(readKey, vaultId) {
    const mac = await hmacSha256(readKey, `sg-vault-v1:file-id:ref:${vaultId}`);
    return 'ref-pid-muw-' + toHex(mac).slice(0, 12);
  }

  async function decrypt(readKey, data) {                      // data = iv(12) || ciphertext+tag
    const key   = await crypto.subtle.importKey('raw', readKey, 'AES-GCM', false, ['decrypt']);
    const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: data.slice(0, 12) }, key, data.slice(12));
    return new Uint8Array(plain);
  }

  const decryptJson     = async (rk, data) => JSON.parse(td.decode(await decrypt(rk, data)));
  const decryptMetadata = async (rk, b64)  => td.decode(await decrypt(rk, b64Bytes(b64)));

  /* Open a vault read-only. Returns { commitId, message, files, readBytes, readText }
   * where files maps 'path/name' -> { blobId }. */
  async function openVault({ vaultId, readKeyHex, fetchBytes }) {
    const readKey = hexBytes(readKeyHex);
    const refId   = await deriveRefFileId(readKey, vaultId);
    const ref     = await decryptJson(readKey, await fetchBytes('refs/' + refId));
    const commit  = await decryptJson(readKey, await fetchBytes('data/' + ref.commit_id));

    const files = {};
    async function walkTree(treeId, prefix) {
      const tree = await decryptJson(readKey, await fetchBytes('data/' + treeId));
      for (const entry of tree.entries) {
        const name = await decryptMetadata(readKey, entry.name_enc);
        if (entry.tree_id) await walkTree(entry.tree_id, prefix + name + '/');
        else               files[prefix + name] = { blobId: entry.blob_id };
      }
    }
    await walkTree(commit.tree_id, '');

    const readBytes = async path => {
      if (!files[path]) throw new Error('not in vault: ' + path);
      return decrypt(readKey, await fetchBytes('data/' + files[path].blobId));
    };
    return {
      refId,
      commitId : ref.commit_id,
      message  : commit.message_enc ? await decryptMetadata(readKey, commit.message_enc) : null,
      timestamp: commit.timestamp_ms || null,
      files,
      readBytes,
      readText : async path => td.decode(await readBytes(path)),
    };
  }

  return { openVault, deriveRefFileId, decrypt };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = SgitStaticReader;
