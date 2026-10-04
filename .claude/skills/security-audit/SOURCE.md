# Provenance

Vendored copy of the `security-audit` skill from
https://github.com/cloudflare/security-audit-skill (`skills/security-audit/`),
pinned at commit `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8` (2026-09-14). MIT licence — see `LICENSE`.

Unmodified apart from this file and the copied `LICENSE`. Reviewed in full before vendoring:
markdown methodology plus zero-dependency Node validators (`fs`/`path`/`util` only, no network);
`node --test validate-*.test.cjs` → 65/65 pass on Node 22.

To update: re-clone, diff against this directory, re-read every changed file, bump the pin above.
