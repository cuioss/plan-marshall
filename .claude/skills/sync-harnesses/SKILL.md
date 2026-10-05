---
name: sync-harnesses
description: Sync the generated plan-marshall trees into every harness install (Claude, OpenCode, Antigravity), or into one harness with --target
user-invocable: true
mode: script-executor
allowed-tools: Bash
---

# Sync Harnesses Skill (project-local)

Syncs the generated plan-marshall trees into the install location of every
harness. The pipeline is:

```text
marketplace/bundles/  →  target/{claude,opencode,antigravity}/  →  each harness's own install location
```

One engine does the work for all three harnesses: `marketplace/targets/sync.py`.
With no arguments it syncs `claude`, `opencode` and `antigravity`, in that
order, attempting each one even when an earlier one failed. With `--target X`
it syncs that one harness only.

This file is the Claude Code entry point. The same command exists for the other
two harnesses at `.opencode/commands/sync-harnesses.md` and
`.agents/skills/sync-harnesses/SKILL.md`; all three run the same steps and the
same engine invocation.

This skill is **project-local** (lives under `.claude/skills/`) because it only
makes sense for this meta-project: the plan-marshall repository, where the
marketplace bundles are authored. A consumer project that installs
plan-marshall has no generated tree to sync and does not get this command.

## Parameters

`$ARGUMENTS` is passed to the engine verbatim. The flags used most often:

| Flag | Applies to | Description |
|------|------------|-------------|
| `--target NAME` | — | Sync one harness only: `claude`, `opencode` or `antigravity`. Omitted, all three are synced. |
| `--bundles NAME` | every selected target | Restrict the sync to a single bundle. |
| `--dry-run` | every selected target | Report what would be synced; write nothing. |
| `--from-worktree PATH` | `claude` | Read `{PATH}/target/claude/` and compare it against `{PATH}/marketplace/bundles/`, instead of the current checkout. |
| `--source PATH` | single target | Override the source root. Requires `--target`. |
| `--target-dir PATH` | `opencode`, `antigravity` | Override the destination directory. Requires `--target`. |

`python3 marketplace/targets/sync.py --help` prints the authoritative flag set.

## Usage Examples

```text
/sync-harnesses
```

Regenerates and syncs all three harnesses.

```text
/sync-harnesses --target opencode
```

Regenerates and syncs the OpenCode tree only.

```text
/sync-harnesses --target claude --bundles plan-marshall
```

Syncs a single bundle into the Claude install.

## Workflow

### Step 1: Regenerate the selected targets

Regenerate the tree of every harness the run will sync, so the engine reads
current output. With no `--target`, run all three calls; with `--target X`, run
only the call for `X`.

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
executor, which is the form the enforcement hook allows inside a plan worktree;
a direct `./pw` call is denied there. Read each call's outcome from its TOON
`status` — the executor exits `0` even when the build failed.

**When any call reports anything other than `status: success`, STOP before
Step 2.** Report the failing target and the TOON's `log_file`, which holds the
generator output. Do not run the sync at all: the engine would install whatever
the failed target left in its tree, which may be stale or partial. Once the
failure is fixed, re-run the command; to sync only the targets that did
regenerate, re-run with `--target X` for each of them.

When `--from-worktree PATH` is passed, the Claude source is that worktree's
`target/claude/`, so the regeneration belongs in that worktree.

### Step 2: Run the sync engine

```bash
python3 marketplace/targets/sync.py $ARGUMENTS
```

No arguments means all three harnesses; `--target X` means one.

### Step 3: Inspect the result

**All-targets run** — the engine prints one aggregate document:

- `status` — `success` when every harness synced, `partial` when some did,
  `error` when none did.
- `targets[3]{target,status,summary_message}` — one row per harness.
- One result block per harness (`claude:`, `opencode:`, `antigravity:`) carrying
  that harness's own fields.

On `partial` or `error`, read the `summary_message` of every row whose `status`
is not `success`, then re-run that harness alone with `--target X`.

**Single-target run** — the engine prints that harness's own document.

**The Claude result** carries `guard_outcome` only when the staleness guard
refused before any bundle was attempted. Act on the kind: `stale` → the
generated tree is missing, empty or behind `marketplace/bundles/`, so regenerate
it (Step 1); `probe_failed` → a probe could not run, so the tree's freshness is
unknown and the remedy is to repair the probe the `summary_message` names, not
to regenerate. Otherwise inspect `synced[N]{bundle,version,status}` and the
optional `failed[M]{bundle,error}` table, and retry a failed bundle with
`--target claude --bundles NAME`.

### Step 4: Reconcile the build daemon when the Claude target synced

Run the reconcile only when the Claude target reports `status: success` — the
`claude` row of `targets[]` on an all-targets run, or the document `status` on
a `--target claude` run:

```bash
python3 marketplace/targets/claude/reconcile_daemon.py
```

Skip it when the Claude target was not selected, when its status is `partial` or
`error` (the install is incomplete), and on a `--dry-run` (nothing was written).

A successful Claude sync is what makes a running `marshalld` stale: the daemon
is pinned to the previous bundle copy. The reconcile upgrades an **idle** stale
daemon to the verified pin and leaves a **busy** one running with the deferral
recorded in a `reconcile-owed` marker. An absent or disabled build server is a
silent no-op. Read the TOON `action` / `display_detail` and surface it; a
`defer` is reported, never swallowed.

## Session reload before the next dispatch

> **Reload the session's plugin set after a Claude sync.** Claude Code's agent
> registry is **session-pinned at session start**: it scans the installed
> plugins once when the session boots and never re-scans mid-session. A sync
> that adds agent files — for example newly emitted
> `execution-context-{level}` variants — produces files the already-running
> session **cannot see**. Dispatching against a freshly emitted agent from the
> same session fails with
> `Agent type 'plan-marshall:execution-context-{level}' not found` even though
> the file exists on disk.
>
> **Operational guardrail:** after every `/sync-harnesses` run that synced the
> Claude target and may have altered the agent set, run `/reload-plugins` before
> issuing a dispatch against a newly emitted agent. A full session restart is
> the fallback.

## Critical Rules

- Do **not** modify source files — the command writes only to the harness
  install locations.
- The Claude staleness guard is non-negotiable: when `target/claude/` is missing
  or stale, regenerate it (Step 1) rather than bypassing the guard.

## Related

- `project:finalize-step-deploy-target` (phase-6-finalize) — generates the
  target trees this command consumes.
- `project:finalize-step-sync-plugin-cache` (phase-6-finalize) — the finalize
  step that runs the same engine after a landing.
- `/marshall-steward` — project configuration, including executor regeneration.
