[🏠 Deploy Hub](../00-START-HERE.md) › **Storage modes**

# Storage Modes

| Mode | Data lives | Survives restart | Use for |
|---|---|---|---|
| `memory` | process RAM | ✗ (by design) | agentic workflows, scratch vaults, demos, CI — and fully air-gapped runs (zero external calls) |
| `disk` | a directory / mounted volume | ✓ (if mounted) | single-host appliances (Docker volume, EC2 EBS) |
| `s3` | an S3 bucket | ✓ | production, multi-replica, durability + lifecycle policies |

Selection: explicit `SEND__STORAGE_MODE` → AWS credentials present → `SEND__DISK_PATH` set →
memory. **Memory mode is a feature, not a fallback** — when the compute disappears, so does
the data, and for ephemeral agent-to-agent work that is exactly right.
