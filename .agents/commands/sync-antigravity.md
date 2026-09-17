---
description: Deploy the generated Antigravity tree into the Antigravity plugin directory
---

Deploy the generated Antigravity tree into the Antigravity plugin directory.

Regenerate the target tree, then run the deploy engine with the `run_command` tool:

```bash
./pw generate-antigravity
python3 marketplace/targets/sync.py --target antigravity $ARGUMENTS
```

Report the TOON summary: `status`, `target`, `source`, `destination`,
`skills_count`, `agents_count`, `commands_count`, `assets_count`,
`deployed_count`, `removed_count`, `summary_message`, and any pruned stale entries.

Useful flags (pass via $ARGUMENTS): `--target-dir PATH` for a staging
destination, `--bundles NAME` to scope to one bundle, `--dry-run` to print
actions without touching the filesystem.
