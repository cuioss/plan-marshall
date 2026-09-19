---
name: sync-antigravity
description: Deploy the generated Antigravity tree into the Antigravity plugin directory. Use when syncing or deploying plan-marshall bundles to Antigravity.
---

# Sync Antigravity

Deploy the generated Antigravity tree into the Antigravity plugin directory.

## Instructions

When this skill is invoked:

1. Regenerate the target tree:
   ```bash
   ./pw generate-antigravity
   ```

2. Run the deploy engine:
   ```bash
   python3 marketplace/targets/sync.py --target antigravity $ARGUMENTS
   ```

3. Report the TOON summary output:
   - `status`
   - `target`
   - `source`
   - `destination`
   - `skills_count`, `agents_count`, `commands_count`, `assets_count`
   - `deployed_count`, `removed_count`
   - `summary_message`
   - Any pruned stale entries

### Useful Flags
Pass via `$ARGUMENTS`:
- `--target-dir PATH`: specify a custom staging destination
- `--bundles NAME`: scope sync to a specific bundle
- `--dry-run`: print actions without modifying the filesystem
