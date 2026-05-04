---
name: sync-plugin-cache
description: Synchronize all marketplace bundles to the Claude plugin cache
user-invocable: true
allowed-tools: Bash
---

# Sync Plugin Cache Skill

Synchronizes all bundles from `marketplace/bundles/` to the Claude plugin cache at `~/.claude/plugins/cache/plan-marshall/`.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--from-worktree PATH` | optional | Source the rsync from a worktree's `marketplace/bundles/` rather than the main checkout. Use when a plan-in-flight is refactoring a marketplace bundle and downstream tasks need the cache to reflect the worktree's uncommitted state. |
| `--bundle NAME` | optional, requires `--from-worktree` | Restrict the sync to a single bundle. Without this flag, every bundle under `--from-worktree` is synced. Cache versions are still resolved per-bundle from the worktree's `plugin.json`. |

When neither parameter is supplied, behaviour is unchanged: every bundle under cwd's `marketplace/bundles/` is rsynced into cache.

## Usage Examples

```bash
/sync-plugin-cache
```

Syncs all bundles from cwd `marketplace/bundles/` to cache (default flow).

```bash
/sync-plugin-cache --from-worktree /Users/oliver/git/plan-marshall/.claude/worktrees/my-plan --bundle plan-marshall
```

Scoped sync from a worktree: rsyncs only the named bundle's worktree-resident files into the cache, leaving the cache copies of other bundles intact. The version is resolved from the worktree's `plugin.json`, so a worktree-only version bump is honoured.

## Workflow

### Step 1: Identify Bundles and Versions

Enumerate bundles and their plugin.json versions by invoking the helper script. When syncing from cwd (default flow):

```bash
python3 .claude/skills/sync-plugin-cache/scripts/list_bundles_and_versions.py
```

When syncing from a worktree, pass `--source-root` so the helper reads the worktree's `plugin.json` (versions can differ between cwd and worktree):

```bash
python3 .claude/skills/sync-plugin-cache/scripts/list_bundles_and_versions.py --source-root {worktree_path}
```

The script prints a TOON `bundles[N]{name,version}` table — each row is `{bundle}`,`{version}`. Bundles whose `plugin.json` is missing or malformed emit `version: unknown`. Parse the rows and reuse the `{bundle}` / `{version}` pairs as template substitutions in Step 3.

When `--bundle NAME` is supplied alongside `--from-worktree`, filter the parsed rows down to that single bundle before Step 3.

### Step 2: Determine Cache Location

The plugin cache location is: `~/.claude/plugins/cache/plan-marshall/`

Each bundle is cached at: `~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/`

**IMPORTANT**: The version folder is required to match Claude Code's installation structure.

### Step 3: Sync Each Bundle

**CRITICAL**: Execute ALL rsync commands in PARALLEL using separate Bash tool calls in a single message. Do NOT use a for loop or sequential execution.

For each bundle found, invoke a separate Bash tool call using the version from Step 1.

Default flow (sync from cwd):
```bash
rsync -av --delete marketplace/bundles/{bundle}/ ~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/
```

Worktree flow (sync from a worktree's bundles tree):
```bash
rsync -av --delete {worktree_path}/marketplace/bundles/{bundle}/ ~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/
```

The `--delete` flag ensures removed files are also removed from cache.

**NOTE**: Always use the version from each bundle's `plugin.json`, not a hardcoded value. With `--from-worktree`, the version comes from the worktree's `plugin.json` (which may differ from the cwd / cache copy).

### Step 4: Display Summary

Show sync results listing each bundle synchronized and the cache location.

## Critical Rules

- Always use rsync with `--delete` to ensure cache matches source exactly
- Do NOT modify source files, only copy to cache
- If rsync fails, show error and continue with remaining bundles

## Related

- `/marshall-steward` - Project configuration including cache regeneration
- CLAUDE.md - Documents the plugin cache sync pattern
