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
| `--repin` | `claude` | After the cache sync, repin the plugin registry to the synced version. Without it the registry is only read. Writes nothing under `--dry-run`. |
| `--registry-path PATH` | `claude` | The plugin registry file the `registry_parity` block reads, instead of the plugin manager's own file. |
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

- `status` — `success` only when every harness reported `success`, `partial`
  when some did, `error` when none did.
- `targets[3]{target,status,summary_message}` — one row per harness.
- One result block per harness (`claude:`, `opencode:`, `antigravity:`) carrying
  that harness's own fields.

On `partial` or `error`, read the `summary_message` of every row whose `status`
is not `success`, then re-run with `--target X` each harness whose **own
install did not sync**: for OpenCode and Antigravity a `status` other than
`success`, for Claude a `cache_status` other than `success` (read from the
`claude:` result block). A Claude row that is `partial` only because its
registry is behind is not such a row — see the Claude result below.

**Single-target run** — the engine prints that harness's own document.

**The Claude result** carries `guard_outcome` only when the staleness guard
refused before any bundle was attempted. Act on the kind: `stale` → the
generated tree is missing, empty or behind `marketplace/bundles/`, so regenerate
it (Step 1); `probe_failed` → a probe could not run, so the tree's freshness is
unknown and the remedy is to repair the probe the `summary_message` names, not
to regenerate. Otherwise inspect `synced[N]{bundle,version,status}` and the
optional `failed[M]{bundle,error}` table, and retry a failed bundle with
`--target claude --bundles NAME`.

The Claude result separates the cache sync from the registry pin with two
further members:

- `cache_status` — `success`, `partial` or `error`: the outcome of the cache
  sync alone. `status` differs from it only when a registry that is behind
  lowered a `success` to `partial`.
- `registry_parity` — the last block of the result when present. It lists one
  `entries` row per plan-marshall registry entry and ends with a `verdict`,
  which is exactly one of:

| `verdict` | Meaning | What to do |
|-----------|---------|------------|
| `in_parity` | Every judged registry entry is pinned at the synced version. | Nothing. |
| `behind` | An entry is pinned older than the synced version. The Claude `status` is `partial`, and a `--target claude` run exits `3`. | Repin with `registry_pin.py --apply` — see [After the sync](#after-the-sync). Step 5 only reports the pin. |
| `ahead` | An entry is pinned newer than the synced version. | Nothing — reported, not an error. A repin never moves a pin backwards. |
| `unreadable` | Parity could not be established; the block's `reason` says why. | Nothing — reported, not an error. |

Read a Claude row that is `partial` through its `cache_status`. With
`cache_status: success` the cache install is complete and only the registry pin
is stale, so the remedy is the repin, **not** a `--target claude` re-run —
re-running the sync would mirror the same cache again and leave the same pin.
The repin is a write the operator asks for: `registry_pin.py --apply`, as
[After the sync](#after-the-sync) describes, or the opt-in of the
`project:finalize-step-sync-plugin-cache` step at finalize. Step 5 runs the
same script without `--apply`, which reports the pin and writes nothing.
An all-targets run reports that case and exits `1`; exit
code `3` is the `--target claude` form of the same finding.

### Step 4: Reconcile the build daemon when the Claude cache synced

Run the reconcile only when the Claude result reports `cache_status: success` —
read from the `claude:` result block on an all-targets run, or from the
document on a `--target claude` run. The `targets[]` row carries no
`cache_status`, so the row is not where this gate is read:

```bash
python3 marketplace/targets/claude/reconcile_daemon.py
```

Skip it when the Claude target was not selected, when `cache_status` is
`partial` or `error` (the install is incomplete), and on a `--dry-run` (nothing
was written). A Claude `status: partial` caused only by a `behind` registry
does **not** skip the reconcile: the cache is complete, and the cache is what
the daemon is reconciled against.

A successful Claude sync is what makes a running `marshalld` stale: the daemon
is pinned to the previous bundle copy. The reconcile upgrades an **idle** stale
daemon to the verified pin and leaves a **busy** one running with the deferral
recorded in a `reconcile-owed` marker. An absent or disabled build server is a
silent no-op. Read the TOON `action` / `display_detail` and surface it; a
`defer` is reported, never swallowed.

### Step 5: Report the registry pin when the Claude cache synced

Under the same `cache_status: success` gate as Step 4 — and with the same skip
conditions, including that a `partial` caused only by a `behind` registry does
**not** skip it — run the repin script in its report form:

```bash
python3 marketplace/targets/claude/registry_pin.py
```

Without a flag the script is a dry run that is always printed and writes
nothing: one `entries` row per plan-marshall registry entry with its version
before and after, then the `registry_parity` verdict (`in_parity`, `behind`,
`ahead` or `unreadable`) as the last line. Surface the verdict.

Writing the registry is opt-in. Passing `--apply` to the same script is the
write; so is `--repin` on the engine call of Step 2. Neither is run unless the
operator asks for it.

## After the sync

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
