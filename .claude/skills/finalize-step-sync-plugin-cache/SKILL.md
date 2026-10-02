---
lane:
  class: derived-state
  cost_size: XS
name: finalize-step-sync-plugin-cache
description: Sync every harness install (Claude cache, OpenCode, Antigravity) from target/ via the unified sync engine
mode: script-executor
order: 85
mutates_source: false
default_on: false
presets: []
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Finalize Step — Sync Harness Installs (project-local)

Project-local executor for `project:finalize-step-sync-plugin-cache`.
Invokes the unified sync engine `marketplace/targets/sync.py` with no
`--target`, so one call syncs all three harnesses from their generated
trees:

| Harness | Source | Install location |
|---------|--------|------------------|
| `claude` | `target/claude/` | the versioned plugin cache `~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/` |
| `opencode` | `target/opencode/` | `~/.config/opencode/` |
| `antigravity` | `target/antigravity/` | `~/.gemini/config/plugins/plan-marshall/` |

The step id names the Claude plugin cache; the step itself syncs every
harness install. It is the finalize-time counterpart of the
project-local `/sync-harnesses` command, which runs the same engine.

This step is **project-local** rather than a `default:` built-in for
the same reason as `project:finalize-step-deploy-target`: the sync only
makes sense for this repo (the plan-marshall meta-project). Consumer
projects have nothing to publish, so they don't get this step seeded
into their `marshal.json` defaults.

This step runs on the main checkout post-merge, after
`project:finalize-step-deploy-target` has regenerated the three target
trees from the merged source tree. Syncing the harness installs here
means the next session boot and this sync read the same authoritative
content. This step does not regenerate: the staleness guard below is
the check that the Claude tree it consumes is current.

## Staleness guard

The Claude leg of the engine lives in
`marketplace/targets/claude/cache_sync.py`. It refuses to mirror
`target/claude/` into the cache unless the tree is proven current
relative to `marketplace/bundles/`. The OpenCode and Antigravity legs
carry no staleness guard; they refuse only a missing or empty source
tree.

The guard runs these checks in order:

1. `target/claude/` exists and holds at least one bundle.
2. Every source bundle the Claude emitter selects is present in
   `target/claude/`. The expected set is the bundles under
   `marketplace/bundles/` whose own `.claude-plugin/plugin.json` admits
   `claude` through its `targets` declaration — the field absent means
   every target, the field present means the listed targets only. A
   bundle scoped to other harnesses is never expected in the Claude
   tree; a claude-admitting bundle missing from it is refused.
3. The emit sentinel `target/claude/.emit-marker.json`, written by
   `project:finalize-step-deploy-target`, exists and carries a
   `source_tree_fingerprint`.
4. The fingerprint recomputed over `marketplace/bundles/` (git's native
   `ls-files` / `hash-object` primitives) matches the sentinel's.
5. Every file under `target/claude/` matches the per-file hash manifest
   the sentinel records in `file_hashes`.

A refusal is discriminated by kind, carried in the Claude result block
as `guard_outcome`:

| `guard_outcome` | Meaning | Remedy |
|-----------------|---------|--------|
| `stale` | A check ran and observed a staleness condition: the tree or sentinel is missing, a claude-admitting bundle was not emitted, the source changed since the last emit, or the tree drifted from its manifest | Re-run `project:finalize-step-deploy-target` |
| `probe_failed` | A check could not run at all: a bundle's `plugin.json` could not be read, the fingerprint helper would not import, or `git` would not answer. The tree's freshness is unknown | Repair the probe the `summary_message` names; regenerating is not the fix |

On either kind the Claude result reports `status: error` with the
refusal text in `summary_message`, and no bundle is attempted.

The Phase 6 ordering (`project:finalize-step-deploy-target` at 81 →
`project:finalize-step-sync-plugin-cache` at 85) means the sentinel is
written immediately before this step reads it, so the guard normally
passes on the first try. A `stale` refusal here points at deploy-target
having been skipped or having failed for the Claude target, or at
concurrent edits to `marketplace/bundles/` between emit and sync.

The `--skip-staleness-guard` flag remains the escape hatch for tests and
recovery flows. Phase 6 never invokes it; only operators do, after
diagnosing why the guard refused.

## Ordering

The canonical Phase 6 ordering surrounding this step is:

```text
default:branch-cleanup (70) →
project:finalize-step-deploy-target (81) →
project:finalize-step-sync-plugin-cache (85) →
default:record-metrics (990)
```

`order: 85` places this step immediately after
`project:finalize-step-deploy-target` (so the installs mirror the
just-regenerated `target/` content), post-`branch-cleanup` on the main
checkout. This step is the single project-level owner of on-main
executor regeneration: once the Claude target has synced it regenerates
`.plan/execute-script.py` against the freshly-synced cache (Execution
step 3). `integrate_into_main` performs the move-back only and does NOT
regenerate the executor — the executor stays a per-tree derived artifact
(ADR-002). Coupling regen to this step (the canonical "sync → regenerate
executor" sequence) closes the no-worktree staleness gap: the regen runs
in BOTH worktree and no-worktree finalize flows because it is just a
finalize step, not a move-back side effect.

## Inputs

- `{plan_id}` — required. Used for logging.

## Execution

Inline-only — this step does NOT delegate to a Task agent. The sync
engine is a fast Python script with deterministic output.

### 1. Invoke the unified sync engine

```bash
python3 marketplace/targets/sync.py
```

With no `--target` the engine attempts `claude`, `opencode` and
`antigravity` in that order — each one even when an earlier one failed —
and prints one aggregate TOON document:

- `status` — `success` | `partial` | `error`.
- `targets[3]{target,status,summary_message}` — one row per harness.
- One result block per harness (`claude:`, `opencode:`, `antigravity:`)
  carrying that harness's own fields: `synced_count` and
  `synced[N]{bundle,version,status}` for Claude, `deployed_count` and
  `removed_count` for OpenCode and Antigravity.

The engine exits `0` only on aggregate `success`. Read the outcome from
the document's `status`, not from the exit code alone.

### 2. Parse the result

| Aggregate `status` | Meaning | Outcome |
|--------------------|---------|---------|
| `success` | Every harness reported `success` | `outcome=done` |
| `partial` | At least one harness synced and at least one did not | `outcome=failed`; surface the `summary_message` of every `targets[]` row whose `status` is not `success` |
| `error` | No harness synced | `outcome=failed`; surface every row's `summary_message` |

One failing harness never hides the other two: the `targets[]` table
reports each harness on its own row, and Steps 3 and 3b below key on the
`claude` row alone.

### 3. Regenerate the on-main executor (when the Claude target synced)

When the `claude` row of `targets[]` reports `status: success`,
regenerate `.plan/execute-script.py` against the freshly-synced host
cache. This runs on the main checkout, so the generator's cwd-relative
resolution writes main's executor with mappings that point at the
just-synced cache — refreshing the on-main mapping after a plan that
changed the marketplace script *set*. This step is the meta-project-only
owner of on-main executor regeneration, and it runs in BOTH worktree and
no-worktree finalize flows (closing the no-worktree staleness gap).

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate
```

Regeneration is **unconditional-after-successful-sync** of the Claude
target (always re-deriving the executor from the fresh cache is cheap,
deterministic, and eliminates the staleness class without a gating
heuristic) and **non-fatal**: a non-zero exit or failure logs a WARN and
the step still records its sync outcome — finalize must not block on a
mapping refresh.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[STATUS] (project:finalize-step-sync-plugin-cache) On-main executor regeneration failed (non-fatal); run /marshall-steward to recover"
```

The gate is the `claude` row, not the aggregate: when OpenCode or
Antigravity failed but Claude synced, the cache is complete and the
regeneration still runs, while the step records `outcome=failed` for the
failing harness. When the `claude` row reports anything other than
`success`, SKIP regeneration — the cache is incomplete or untouched, so
regenerating against it would be wrong; the step records the failure
(Step 4) and an operator recovers.

### 3b. Reconcile the build daemon (when the Claude target synced)

The cache bump the Claude leg just performed is exactly what makes a
running `marshalld` stale: the daemon is version-pinned to the OLD
bundle copy while the fresh cache now carries a newer one. When the
`claude` row reports `status: success` (and after the executor regen
above), run the meta-project-only reconcile so an **idle** stale daemon
is upgraded to the verified pin and a **busy** one is left running with
the deferral recorded:

```bash
python3 marketplace/targets/claude/reconcile_daemon.py
```

The script queries `manage-build-server status` and applies the idle-conditional
contract: idle-and-stale → `upgrade` (drain-then-start-verified); busy-and-stale
(anything in flight or queued) or an undeterminable running provenance →
**defer** (never drain a live build), leaving a readable `reconcile-owed` marker;
down-but-enrolled → plain `start`; already-current → no-op. An absent/disabled
build server (or a session without the executor) is a **silent no-op** via the
script's fail-open adapters, so this changes no shared-daemon behaviour and a
repository not using marshalld is unaffected.

Like the executor regen, the reconcile is **non-fatal**: it never blocks finalize.
Read its `action` / `display_detail` from the TOON and surface a one-line detail;
a `defer` is reported (the `reconcile-owed` marker persists it), never swallowed.
When the `claude` row reports anything other than `success`, SKIP the
reconcile — the cache is incomplete.

### 4. Mark step complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step project:finalize-step-sync-plugin-cache \
  --outcome {done|failed} \
  --display-detail "{display_detail}"
```

`{display_detail}` names the per-target result. It is plain ASCII and
at most 80 characters (the limit is owned by
`phase-6-finalize/standards/external-step-contract.md`), so it carries
counts and tokens only; free-form text goes to the work log.

On aggregate `status: success`, it is
`"claude {synced_count}, opencode {deployed_count}, antigravity {deployed_count} synced; regen ok"`,
each count read from that harness's result block. When the Step 3 regen
exited non-zero, end it with `"; regen failed"` instead — the sync
outcome is still `done`, and the Step 3 WARNING line carries the remedy.
When the Step 3b reconcile did anything other than a plain no-op, append
`"; daemon {action}"` with the reconcile's `action` token (`upgrade`,
`defer` or `start`), so a deferral is visible at the step level and not
only in the marker. The reconcile's own `display_detail` is free-form
and is logged, not appended:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (project:finalize-step-sync-plugin-cache) Daemon reconcile: {reconcile_display_detail}"
```

On aggregate `status: partial` or `status: error`, it is
`"failed: {targets} (details in work log)"`, where `{targets}` is the
comma-separated names of every harness whose row is not `success`. When
the Claude target synced in a `partial` run, append
`"; claude synced, regen ok"` so the record states that Steps 3 and 3b
ran. The engine's `summary_message` text is unbounded, so each failing
row's message is logged in full rather than placed in the detail:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[ERROR] (project:finalize-step-sync-plugin-cache) {target}: {summary_message}"
```
