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
   python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "generate-claude"
   ```
   ```bash
   python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "generate-opencode"
   ```
   ```bash
   python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "generate-antigravity"
   ```
   Each call runs the `./pw generate-{target}` alias through the build
   executor. Read its outcome from the TOON `status` (the call exits `0` even
   on failure). When any call reports anything other than `status: success`,
   STOP: report the failing target and the TOON's `log_file`, and do not run
   step 2 — the engine would install whatever the failed target left in its
   tree. To sync only the targets that regenerated, re-run with `--target X`
   for each of them.

2. Run the sync engine:
   ```bash
   python3 marketplace/targets/sync.py $ARGUMENTS
   ```

3. Inspect the result. An all-targets run prints one aggregate document:
   - `status` (`success` | `partial` | `error`)
   - `targets[3]{target,status,summary_message}`
   - one result block per harness; the Claude block also carries:
     - `cache_status` (`success` | `partial` | `error`) — the outcome of the
       cache sync alone
     - `registry_parity` — the last block, ending with a `verdict` that is
       exactly one of `in_parity`, `behind`, `ahead` or `unreadable`

   A single-target run prints that harness's own document. Report the aggregate
   `status` and every `summary_message`.

   `behind` means a registry entry is pinned older than the synced version: the
   Claude `status` is then `partial` and a `--target claude` run exits `3`.
   `ahead` and `unreadable` are reported and are not an error; a repin never
   moves a pin backwards.

   Re-run with `--target X` each harness whose own install did not sync: for
   OpenCode and Antigravity a `status` other than `success`, for Claude a
   `cache_status` other than `success`. A Claude row that is `partial` with
   `cache_status: success` has a complete cache install and only a stale
   registry pin, so its remedy is the repin, not a `--target claude` re-run.
   The repin is the operator's explicit `registry_pin.py --apply` named in the
   block at the end of this file; step 5 only reports the pin.

4. When the Claude result reports `cache_status: success`, reconcile the build
   daemon. Read the field from the `claude:` result block on an all-targets
   run, or from the document on a `--target claude` run — the `targets[]` row
   carries no `cache_status`:
   ```bash
   python3 marketplace/targets/claude/reconcile_daemon.py
   ```
   Skip this step when the Claude target was not selected, its `cache_status`
   is not `success`, or the run was a `--dry-run`. A Claude `status: partial`
   caused only by a `behind` registry does not skip it. Report the TOON
   `action` and `display_detail`.

5. Under the same `cache_status: success` gate and the same skip conditions —
   a `partial` caused only by a `behind` registry does not skip it — report the
   registry pin:
   ```bash
   python3 marketplace/targets/claude/registry_pin.py
   ```
   Without a flag the script is a dry run that is always printed and writes
   nothing; its last line is the `registry_parity` verdict (`in_parity`,
   `behind`, `ahead` or `unreadable`). Report it. Writing the registry is
   opt-in: `--apply` on this script, or `--repin` on the engine call of step 2.

### Useful Flags
Pass via `$ARGUMENTS`:
- `--target NAME`: sync one harness only
- `--bundles NAME`: scope the sync to a specific bundle
- `--dry-run`: print actions without modifying the filesystem
- `--target-dir PATH`: specify a custom staging destination (requires
  `--target opencode` or `--target antigravity`)
- `--repin`: repin the Claude plugin registry to the synced version after the
  cache sync

`python3 marketplace/targets/sync.py --help` prints the authoritative flag set.

> **After a Claude sync — one sequence, in this order.**
>
> 1. **Sync** — the engine call. For Claude it writes a plugin-cache version
>    directory.
> 2. **Repin** — as its own explicit step, point the plugin registry at the
>    synced version with `python3 marketplace/targets/claude/registry_pin.py --apply`.
>    Without `--apply` the script only reports and writes nothing.
> 3. **Fully restart the session** — a session reads the registry once, when it
>    starts, so only a new session loads the repinned version.
>
> `/reload-plugins` alone is not sufficient. It can make newly emitted agents
> visible to a running session, but skill bodies are still loaded from the
> version the registry named when that session started. A restart without the
> repin changes nothing either: the new session reads the same pin.
