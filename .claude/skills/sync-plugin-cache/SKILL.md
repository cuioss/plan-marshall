---
name: sync-plugin-cache
description: Synchronize all marketplace bundles to the Claude plugin cache via the multi-target generator output
user-invocable: true
allowed-tools: Bash
---

# Sync Plugin Cache Skill (project-local)

Synchronizes the Claude Code plugin cache at
`~/.claude/plugins/cache/plan-marshall/` from the multi-target generator
output at `target/claude/`. The pipeline is:

```
marketplace/bundles/  →  target/claude/  →  ~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/
```

The middle hop (`target/claude/`) is produced by the
`project:finalize-step-deploy-target` finalize step or by an explicit
`python3 marketplace/targets/generate.py --target claude --output target/claude`
invocation. This skill consumes that output as its source of truth — it
does **NOT** rsync directly from `marketplace/bundles/`.

This skill is **project-local** (lives under `.claude/skills/`) because
it only makes sense for this meta-project: the plan-marshall repo where
the marketplace bundles are authored. Consumer projects that install
plan-marshall via Claude Code's plugin system have nothing to publish
to a host cache and therefore do not need (and would be confused by) a
`/sync-plugin-cache` slash command.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--from-worktree PATH` | optional | Resolve the source from a worktree-local `target/claude/` rather than the main checkout. Use when a plan-in-flight is refactoring a marketplace bundle and downstream tasks need the cache to reflect the worktree's regenerated output. |
| `--bundle NAME` | optional | Restrict the sync to a single bundle. Cache versions are still resolved per-bundle from the corresponding `target/claude/{bundle}/.claude-plugin/plugin.json`. |

When neither flag is supplied, every bundle under
`{cwd}/target/claude/` is synced.

## Usage Examples

```bash
/sync-plugin-cache
```

Syncs every bundle from cwd's `target/claude/` to the cache.

```bash
/sync-plugin-cache --from-worktree /Users/oliver/git/plan-marshall/.plan/local/worktrees/my-plan --bundle plan-marshall
```

Scoped sync from a worktree: rsyncs only the named bundle's
worktree-resident `target/claude/{bundle}/` into the cache.

## Workflow

### Step 1: Run the consolidated sync engine

Invoke the project-local `sync.py` directly. The script:

1. Resolves the source root (`{worktree_path}/target/claude/` when
   `--from-worktree` is supplied; cwd's `target/claude/` otherwise).
2. Runs the staleness guard — refuses to sync when the source root is
   missing or stale relative to `marketplace/bundles/` (regeneration
   required).
3. Fans out parallel rsync invocations (one per bundle).
4. Aggregates a `synced[N]{bundle,version,status}` TOON table plus a
   summary status (`success` | `partial` | `error`),
   `synced_count`, `failed_count`, and `summary_message`.

```bash
python3 .claude/skills/sync-plugin-cache/scripts/sync.py
```

Worktree-scoped variant:

```bash
python3 .claude/skills/sync-plugin-cache/scripts/sync.py \
  --from-worktree {worktree_path} --bundle {bundle_name}
```

### Step 2: Inspect the summary

The script's TOON output reports each per-bundle status (`success`,
`failed`, `skipped`) plus the aggregate. On `status: error` (no bundles
synced) or `status: partial` (some failed), inspect the `synced` rows
and the optional `failed[N]{bundle,error}` table for diagnostics, then
re-run with `--bundle NAME` to retry the failures individually.

### Step 3: (optional) Enumerate bundle versions

`list_bundles_and_versions.py` prints a TOON `bundles[N]{name,version}`
table from `target/claude/` (or the supplied `--source-root`). The
sync engine consumes this internally; the script is exposed as a
helper for ad-hoc inspection.

```bash
python3 .claude/skills/sync-plugin-cache/scripts/list_bundles_and_versions.py
```

## Critical Rules

- Always use rsync with `--delete` so the cache matches source exactly.
- Do **not** modify source files — the skill only writes to the cache.
- The staleness guard is non-negotiable: if `target/claude/` is missing
  or stale, regenerate first with `marketplace/targets/generate.py`.

## Related

- `/marshall-steward` — project configuration, including cache
  regeneration prompts.
- `project:finalize-step-deploy-target` (phase-6-finalize) — produces
  `target/claude/`, the input this skill consumes.
- `project:finalize-step-sync-plugin-cache` (phase-6-finalize) —
  finalize-step wrapper that calls `sync.py` directly.
