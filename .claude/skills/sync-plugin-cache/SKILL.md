---
name: sync-plugin-cache
description: Synchronize all marketplace bundles to the Claude plugin cache via the multi-target generator output
user-invocable: true
mode: script-executor
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
`uv run python marketplace/targets/generate.py --target claude --output target/claude`
invocation. This skill consumes that output as its source of truth — it
does **NOT** rsync directly from `marketplace/bundles/`.

This skill is **project-local** (lives under `.claude/skills/`) because
it only makes sense for this meta-project: the plan-marshall repo where
the marketplace bundles are authored. Consumer projects that install
plan-marshall via Claude Code's plugin system have nothing to publish
to a host cache and therefore do not need (and would be confused by) a
`/sync-plugin-cache` slash command.

## Bundle vs marketplace artifacts

The generator emits two kinds of artifact under `target/claude/`:

* **Per-bundle directories** — `target/claude/{bundle}/` carry their own
  `.claude-plugin/plugin.json` and are what this skill rsyncs into the
  host cache as `~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/`.
* **Top-level marketplace manifest** — `target/claude/.claude-plugin/marketplace.json`
  is the manifest Claude Code reads when registering `target/claude/`
  as a marketplace. It is NOT a bundle and is NOT synced into the host
  cache. The bundle-vs-non-bundle distinction is enforced by the
  `_is_bundle_dir` predicate in `sync.py` and
  `list_bundles_and_versions.py`: only directories whose own
  `.claude-plugin/plugin.json` exists are treated as bundles.

This is also why the registered Claude Code marketplace path must point
at `target/claude/` rather than `marketplace/`: the source layout has no
expanded variant agents and no flat-bundle marketplace.json. See the
"Registered Marketplace Path" section in the top-level `CLAUDE.md` for
the migration steps.

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
2. Runs the staleness guard, whose refusals are discriminated by kind.
   `stale` — a probe ran and observed the source root missing, carrying
   no bundles, or stale relative to `marketplace/bundles/`; the remedy is
   to regenerate the target tree. `probe_failed` — a probe could not run
   at all (the fingerprint helper would not import, `git` would not
   answer), so nothing was observed about the target tree and its
   freshness is unknown; the remedy repairs the named probe, and the
   message deliberately does NOT carry the regenerate hint, which would
   send the operator to re-run a generator whose output may already be
   current. Both kinds refuse (exit 2); `--skip-staleness-guard` is the
   deliberate override.
3. Fans out parallel rsync invocations (one per bundle).
4. Aggregates a `synced[N]{bundle,version,status}` TOON table plus a
   summary status (`success` | `partial` | `error`),
   `synced_count`, `failed_count`, `summary_message`, and — on a guard
   refusal only — `guard_outcome` (`stale` | `probe_failed`). The
   absence of `guard_outcome` on every other path means no guard verdict
   was reached.

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
`failed`, `skipped`) plus the aggregate.

**When `guard_outcome` is present**, the staleness guard refused before
any bundle was attempted: `synced` and `failed` are both empty by
construction, so there are no rows to inspect and no per-bundle retry to
make. Read `summary_message` and act on the kind — `stale` → regenerate
the target tree (`finalize-step-deploy-target`); `probe_failed` → repair
the probe the message names, because the target tree's freshness is
unknown and regenerating it is not the fix.

**Otherwise**, on `status: error` (no bundles synced) or
`status: partial` (some failed), inspect the `synced` rows and the
optional `failed[N]{bundle,error}` table for diagnostics, then re-run
with `--bundle NAME` to retry the failures individually.

### Step 2b: SESSION RELOAD REQUIRED before next dispatch

> **CRITICAL — Reload the session's plugin set before next dispatch.** Claude
> Code's agent registry is **session-pinned at session start**: it scans
> the plugin cache exactly once when the session boots and never re-scans
> mid-session. A `/sync-plugin-cache` run that adds new agent files —
> e.g., newly-emitted `execution-context-{level}` variants from the
> dynamic-level executor extension point — produces files the
> already-running session **cannot see**. Dispatching against a freshly
> emitted variant from the same session fails with
> `Agent type 'plan-marshall:execution-context-{level}' not found` even
> though the file exists on disk in the cache.
>
> **Operational guardrail:** after every `/sync-plugin-cache` run that
> may have altered the agent set, reload the session's plugin set before
> issuing a dispatch (`Task: plan-marshall:execution-context-{level}`,
> any newly-registered agent, etc.). On Claude `/reload-plugins` refreshes
> the session-pinned registry live; a full session restart is the fallback.
> Sister surfaces (`/marshall-steward` executor regeneration, the
> `variant_emitter.py` module docstring, and the
> `ext-point-dynamic-level-executor` standard) converge on the same
> WHY: the registry is session-pinned at startup, so newly-emitted
> agents are visible only after the session reloads its plugin set.

### Step 2c: Reconcile the build daemon (after a successful sync)

The cache bump this sync performed is exactly what makes a running `marshalld`
stale: the daemon is version-pinned to the OLD bundle copy while the fresh cache
now carries a newer one. After a `success` sync, run the meta-project-only
reconcile so an **idle** stale daemon is upgraded to the verified pin and a
**busy** one is left running with the deferral recorded (SKIP the reconcile on a
`partial` or `error` sync — the cache is incomplete, matching the finalize step):

```bash
python3 .claude/skills/sync-plugin-cache/scripts/reconcile_daemon.py
```

It queries `manage-build-server status` and applies the idle-conditional
contract: idle-and-stale → `upgrade` (drain-then-start-verified); busy-and-stale
(anything in flight or queued) or an undeterminable running provenance →
**defer** (never drain a live build), leaving a readable `reconcile-owed` marker
consumed by the next sync; down-but-enrolled → plain `start`; already-current →
no-op. An absent or disabled build server is a **silent no-op** via fail-open
adapters, so a repository not using marshalld is unaffected and no shared-daemon
behaviour changes. Read the TOON `action` / `display_detail` and surface it; a
`defer` is reported, never swallowed.

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
