---
description: Deploy the generated OpenCode tree into the OpenCode config directory (singular→plural rename)
---

Deploy the generated OpenCode tree into the OpenCode config directory.

Regenerate the target tree, then run the deploy engine with the `bash` tool:

```bash
./pw generate-opencode
python3 .opencode/scripts/sync_opencode.py $ARGUMENTS
```

Report the TOON summary: `status`, `deployed_count`, `removed_count`,
`summary_message`, and any pruned stale entries.

Useful flags (pass via $ARGUMENTS): `--target-dir PATH` for a staging
destination, `--bundles NAME` to scope to one bundle, `--dry-run` to print
actions without touching the filesystem.