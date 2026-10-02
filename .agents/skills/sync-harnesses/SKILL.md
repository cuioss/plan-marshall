---
name: sync-harnesses
description: Sync the generated plan-marshall trees into every harness install (Claude, OpenCode, Antigravity), or into one harness with --target. Use when syncing or deploying plan-marshall bundles to a harness.
mode: script-executor
---

# Sync Harnesses

Sync the generated plan-marshall trees into the install location of every
harness. With no arguments all three harnesses (`claude`, `opencode`,
`antigravity`) are synced; `--target X` syncs one.

## Instructions

When this skill is invoked:

1. Regenerate the selected targets. With no `--target` in `$ARGUMENTS`, run all
   three; with `--target X`, run only the one for `X`:
   ```bash
   ./pw generate-claude
   ```
   ```bash
   ./pw generate-opencode
   ```
   ```bash
   ./pw generate-antigravity
   ```

2. Run the sync engine:
   ```bash
   python3 marketplace/targets/sync.py $ARGUMENTS
   ```

3. Inspect the result. An all-targets run prints one aggregate document:
   - `status` (`success` | `partial` | `error`)
   - `targets[3]{target,status,summary_message}`
   - one result block per harness

   A single-target run prints that harness's own document. Report the aggregate
   `status` and every `summary_message`; for a row whose `status` is not
   `success`, re-run that harness alone with `--target X`.

4. When the Claude target reports `status: success`, reconcile the build
   daemon:
   ```bash
   python3 marketplace/targets/claude/reconcile_daemon.py
   ```
   Skip this step when the Claude target was not selected, did not report
   `success`, or the run was a `--dry-run`. Report the TOON `action` and
   `display_detail`.

### Useful Flags
Pass via `$ARGUMENTS`:
- `--target NAME`: sync one harness only
- `--bundles NAME`: scope the sync to a specific bundle
- `--dry-run`: print actions without modifying the filesystem
- `--target-dir PATH`: specify a custom staging destination (requires
  `--target opencode` or `--target antigravity`)

`python3 marketplace/targets/sync.py --help` prints the authoritative flag set.

A running Claude Code session sees agents a Claude sync newly emitted only
after `/reload-plugins`.
