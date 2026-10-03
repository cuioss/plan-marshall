---
description: Sync the generated plan-marshall trees into every harness install (Claude, OpenCode, Antigravity), or into one harness with --target
---

Sync the generated plan-marshall trees into the install location of every
harness. With no arguments all three harnesses (`claude`, `opencode`,
`antigravity`) are synced; `--target X` syncs one.

Run every command with the `bash` tool, one command per call.

1. Regenerate the selected targets. With no `--target` in $ARGUMENTS, run all
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
   on failure); on `status: error`, report the TOON's `log_file` and do not
   sync that target.

2. Run the sync engine:

   ```bash
   python3 marketplace/targets/sync.py $ARGUMENTS
   ```

3. Inspect the result. An all-targets run prints one aggregate document:
   `status` (`success` | `partial` | `error`), a
   `targets[3]{target,status,summary_message}` table, then one result block per
   harness. A single-target run prints that harness's own document. Report the
   aggregate `status` and every `summary_message`; for a row whose `status` is
   not `success`, re-run that harness alone with `--target X`.

4. When the Claude target reports `status: success`, reconcile the build
   daemon:

   ```bash
   python3 marketplace/targets/claude/reconcile_daemon.py
   ```

   Skip this step when the Claude target was not selected, did not report
   `success`, or the run was a `--dry-run`. Report the TOON `action` and
   `display_detail`.

Useful flags (pass via $ARGUMENTS): `--target NAME` to sync one harness,
`--bundles NAME` to scope to one bundle, `--dry-run` to print actions without
touching the filesystem, `--target-dir PATH` for a staging destination
(requires `--target opencode` or `--target antigravity`).
`python3 marketplace/targets/sync.py --help` prints the authoritative flag set.

A running Claude Code session sees agents a Claude sync newly emitted only
after `/reload-plugins`.
