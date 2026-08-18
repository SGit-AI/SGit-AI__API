[🏠 Deploy Hub](../00-START-HERE.md) › **Security model**

# Security Model (self-hosted)

**Zero-knowledge core:** every vault object is encrypted client-side (AES-256-GCM, keys
derived in the browser/CLI via PBKDF2-600k). Your server stores ciphertext and hashes only.
The operator can see *which* vault IDs exist, sizes, and timing — never contents, never keys.

**The access key (single-key mode):** a self-hosted deployment is protected by one key,
`SGRAPH_SEND__ACCESS_TOKEN`. When set, **every** route requires it — API calls (header
`x-sgraph-access-token`) and browser reads alike. The only open path is the login page,
which stores the key as a browser cookie after verifying it. This key is the deployment's
licence and admission ticket in one.

**Where the key lives:** it's provided at deploy time and stored *nowhere server-side* — not
SSM, not Secrets Manager, not disk. Keep it in a password manager, your CI's secret store, or
an SG/Vault. Rotate by redeploying with a new value.

**Vault keys vs access key:** the access key admits you to the *server*. Vault keys decrypt
*content* — they never reach the server at all. Losing the access key means redeploying;
losing a vault key means that vault's content is gone forever (that's the zero-knowledge deal).
