---
description: Carry a plan-marshall bundle change to a restart-ready machine — regenerate the targets, sync every harness install, refresh the executor, reconcile the daemon and pin the registry in one run
---

Carry a change under `marketplace/bundles/` from the source tree to a machine
whose next session loads it: regenerate the target trees, sync every harness
install, refresh the executor, reconcile the build daemon and pin the plugin
registry. It runs on the main checkout of this repository only, and it is
meta-project-only, like `/sync-harnesses`.

`/sync-harnesses` is the narrow form: it regenerates and syncs, and leaves the
executor regeneration and the registry write to the operator. This command adds
those two follow-ups and ends by naming the restart it cannot perform.

Run every command with the `bash` tool, one command per call.

1. Regenerate the three targets, so the engine reads current output:

   ```bash
   python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "generate-claude"
   ```

   ```bash
   python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "generate-opencode"
   ```

   ```bash
   python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "generate-antigravity"
   ```

   Each call runs the matching `./pw generate-{target}` alias through the build
   executor. Read each call's outcome from its TOON `status`: the call exits `0`
   even when the build failed. When any call reports a `status` other than
   `success`, STOP before step 2 — report the failing target and the TOON's
   `log_file`, because the engine would install whatever the failed target left
   in its tree.

2. Run the sync engine:

   ```bash
   python3 marketplace/targets/sync.py
   ```

   No argument and no target flag: one run syncs `claude`, `opencode` and
   `antigravity`, in that order, attempting each harness even when an earlier one
   failed. A narrower sync is `/sync-harnesses --target NAME`. Then read the
   result, from the document rather than from the exit code: an aggregate
   `status`, a `targets[3]{target,status,summary_message}` table, and one result
   block per harness. The Claude result carries `cache_status` — the outcome of
   the cache sync alone — and, when present, the `registry_parity` block with the
   `verdict` the engine read before step 5 writes.

3. Regenerate the executor. Run this step only when the Claude result reports
   `cache_status: success`, read from the `claude:` result block. A Claude
   `status` of `partial` caused only by a registry that is `behind` leaves the
   cache complete, so it does not skip this step, and one failing harness never
   skips it while the Claude cache synced:

   ```bash
   python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate
   ```

   When `cache_status` reports anything else, the cache is incomplete or
   untouched: skip steps 4 and 5 as well, because there is nothing to reconcile
   or to pin against.

4. Under the same `cache_status: success` gate, reconcile the build daemon. The
   cache bump is what makes a running `marshalld` stale: an idle stale daemon is
   upgraded to the verified pin, a busy one is left running with the deferral
   recorded, and an absent or disabled build server is a silent no-op:

   ```bash
   python3 marketplace/targets/claude/reconcile_daemon.py
   ```

   Read the TOON `action` and `display_detail` and surface them; a deferral is
   reported, never swallowed.

5. Under the same `cache_status: success` gate, pin the plugin registry, as its
   own step: writing the registry is never part of the cache sync. Running this
   command is the operator's consent to the write — the machine-local
   `registry-repin` setting stays the opt-in of the
   `project:finalize-step-sync-plugin-cache` finalize step and is not read here:

   ```bash
   python3 marketplace/targets/claude/registry_pin.py --apply
   ```

   An entry pinned ahead of the synced version stays untouched and is reported,
   because the script never moves a pin backwards. The script prints one `entries`
   row per plan-marshall registry entry and ends with `registry_parity`. That last
   value is the run's final registry verdict: `in_parity`, `behind`, `ahead` or
   `unreadable`. Report it; a `behind` verdict after an `--apply` run is a failure
   of the write, not of the cache.

Report every harness row whose own install did not sync, with that row's
`summary_message`: for OpenCode and Antigravity a row `status` other than
`success`, for Claude a `cache_status` other than `success`. A `summary_message`
that reports a refusal because of a symbolic link in the install location is
resolved by removing or relocating the named link, never by a re-run.

The same command exists for the other two harnesses at
`.claude/skills/apply-changes/SKILL.md` and `.agents/skills/apply-changes/SKILL.md`;
all three run the same steps, in the same order, with the same commands.

> **The run ends with a restart — this command cannot perform it.**
>
> 1. **Fully restart the session** — a session reads the plugin registry once,
>    when it starts, so only a new session loads the version the repin just wrote.
>
> `/reload-plugins` alone is not sufficient. It can make newly emitted agents
> visible to a running session, but skill bodies are still loaded from the version
> the registry named when that session started.
