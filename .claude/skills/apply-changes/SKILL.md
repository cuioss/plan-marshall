---
name: apply-changes
description: Carry a plan-marshall bundle change to a restart-ready machine — regenerate the targets, sync every harness install, refresh the executor, reconcile the daemon and pin the registry in one run
user-invocable: true
mode: script-executor
allowed-tools: Bash
---

# Apply Changes Skill (project-local)

Carries a change under `marketplace/bundles/` from the source tree to a machine
whose next session loads it. The pipeline is:

```text
marketplace/bundles/  →  target/{claude,opencode,antigravity}/  →  each harness install  →  executor  →  registry
```

This file is the Claude Code entry point. The same command exists for the other
two harnesses at `.opencode/commands/apply-changes.md` and
`.agents/skills/apply-changes/SKILL.md`; all three run the same steps, in the same
order, with the same commands.

It runs on the **main checkout of this repository only** and it is
**meta-project-only**, like `/sync-harnesses`: a consumer project that installs
plan-marshall has no generated tree to carry forward and does not get this
command.

`/sync-harnesses` is the narrow form. It regenerates and syncs, and leaves the
executor regeneration and the registry write to the operator. This command adds
those two follow-ups, in the order the cache bump makes them necessary, and ends
by naming the restart it cannot perform for the operator.

## Workflow

### Step 1: Regenerate the three targets

Regenerate every target tree, so the engine reads current output.

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
executor. Read each call's outcome from its TOON `status`: the executor exits `0`
even when the build failed.

**When any call reports a `status` other than `success`, STOP before Step 2.**
Report the failing target and the TOON's `log_file`, which holds the generator
output. Do not run the sync at all: the engine would install whatever the failed
target left in its tree, which may be stale or partial. Once the failure is
fixed, re-run the command.

### Step 2: Run the sync engine

```bash
python3 marketplace/targets/sync.py
```

No argument and no target flag: one run syncs `claude`, `opencode` and
`antigravity`, in that order, attempting each harness even when an earlier one
failed. A narrower sync is `/sync-harnesses --target NAME`.

Then read the result, from the document rather than from the exit code. An
all-targets run prints one aggregate document with `status`, a
`targets[3]{target,status,summary_message}` table, and one result block per
harness (`claude:`, `opencode:`, `antigravity:`). The Claude result separates the
cache sync from the registry pin: `cache_status` is the outcome of the cache sync
alone, and `registry_parity` — when present, the last block — carries the
`verdict` the engine read before the repin of Step 5.

### Step 3: Regenerate the executor

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate
```

Run this step only when the Claude result reports `cache_status: success`, read
from the `claude:` result block. A Claude `status` of `partial` caused only by a
registry that is `behind` leaves the cache complete, so it does not skip this
step, and one failing harness never skips it while the Claude cache synced. The
regeneration is cheap, deterministic, and a no-op whenever the script set is
unchanged.

When `cache_status` reports anything else, the cache is incomplete or untouched:
skip Steps 4 and 5 as well, because there is nothing to reconcile or to pin
against.

### Step 4: Reconcile the build daemon

```bash
python3 marketplace/targets/claude/reconcile_daemon.py
```

Under the same `cache_status: success` gate as Step 3. The cache bump is what
makes a running `marshalld` stale: the daemon is pinned to the previous bundle
copy. An idle stale daemon is upgraded to the verified pin, a busy one is left
running with the deferral recorded in a `reconcile-owed` marker, and an absent or
disabled build server is a silent no-op. Read the TOON `action` and
`display_detail` and surface them; a deferral is reported, never swallowed.

### Step 5: Pin the plugin registry

```bash
python3 marketplace/targets/claude/registry_pin.py --apply
```

Under the same `cache_status: success` gate, and as its own step: writing the
registry is never part of the cache sync. Running this command is the operator's
consent to the write — the machine-local `registry-repin` setting stays the
opt-in of the `project:finalize-step-sync-plugin-cache` finalize step and is not
read here. An entry pinned ahead of the synced version stays untouched and is
reported, because the script never moves a pin backwards.

The script prints one `entries` row per plan-marshall registry entry and ends
with `registry_parity`. That last value is the run's final registry verdict:
`in_parity`, `behind`, `ahead` or `unreadable`. Report it. A `behind` verdict
after an `--apply` run is a failure of the write, not of the cache; `ahead` and
`unreadable` are reported and are not errors.

## Reporting

Report every harness row whose own install did not sync, with that row's
`summary_message`: for OpenCode and Antigravity a row `status` other than
`success`, for Claude a `cache_status` other than `success`. One failing harness
never hides another harness's result and never skips the steps above while the
Claude cache synced. When a `summary_message` says the sync was refused because
of a symbolic link in the install location, re-running does not help: remove or
relocate the named link first.

## Related

- `.claude/skills/sync-harnesses/SKILL.md` — the narrow form: regenerate and sync.
- `project:finalize-step-deploy-target` (phase-6-finalize) — generates the target
  trees this command consumes.
- `project:finalize-step-sync-plugin-cache` (phase-6-finalize) — the finalize
  step that runs the same engine after a landing.
- `doc/adr/025-The_harness_sync_repins_the_plugin_registry_only_on_operator_opt-in.adoc`
  — why the registry write stays a separate, operator-invoked step.

## After the run

> **The run ends with a restart — this command cannot perform it.**
>
> 1. **Fully restart the session** — a session reads the plugin registry once,
>    when it starts, so only a new session loads the version the repin just wrote.
>
> `/reload-plugins` alone is not sufficient. It can make newly emitted agents
> visible to a running session, but skill bodies are still loaded from the version
> the registry named when that session started.
