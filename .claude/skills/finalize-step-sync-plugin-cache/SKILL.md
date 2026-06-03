---
name: finalize-step-sync-plugin-cache
description: Synchronize the Claude plugin cache from target/claude/ via the consolidated sync engine
order: 85
---

# Finalize Step — Sync Plugin Cache (project-local)

Project-local executor for `project:finalize-step-sync-plugin-cache`.
Invokes the consolidated `sync.py` engine in the project-local
`.claude/skills/sync-plugin-cache/` skill to mirror `target/claude/`
into the host plugin cache.

This step is **project-local** rather than a `default:` built-in for
the same reason as `project:finalize-step-deploy-target`: the cache-
sync only makes sense for this repo (the plan-marshall meta-project).
Consumer projects have nothing to publish, so they don't get this step
seeded into their `marshal.json` defaults.

This step runs on the main checkout post-merge, after
`project:finalize-step-deploy-target` has regenerated `target/claude/`
from the merged source tree. Syncing the host cache here means the
next session boot and this sync read the same authoritative content.

## Staleness guard

`sync.py` refuses to mirror `target/claude/` into the cache unless the
emit sentinel proves the target tree is current. The sentinel is a
JSON file written by `project:finalize-step-deploy-target` at
`target/claude/.emit-marker.json`. It carries an ISO-8601
`emit_completed_at` timestamp and a `source_tree_fingerprint` computed
from git's native `ls-files` / `hash-object` primitives over
`marketplace/bundles/`.

The guard refuses (exit code 2, `status: error`) in three cases:

| Case | Cause | `summary_message` shape |
|------|-------|-------------------------|
| Sentinel absent | `project:finalize-step-deploy-target` was not run | `staleness_guard: sentinel missing or unreadable at {path} — run finalize-step-deploy-target first.` |
| Sentinel unparseable / missing fingerprint | Corrupted or hand-edited sentinel | `staleness_guard: sentinel ... is missing source_tree_fingerprint.` |
| Fingerprint mismatch | Source tree changed since last emit | `staleness_guard: source tree changed since last emit — re-run finalize-step-deploy-target.` |

The Phase 6 ordering (`project:finalize-step-deploy-target` at 80 →
`project:finalize-step-sync-plugin-cache` at 85) means the sentinel is
written immediately before this step reads it, so the guard normally
passes on the first try. A failure here points at deploy-target having
been skipped, or at concurrent edits to `marketplace/bundles/` between
emit and sync (which would also invalidate the cached output).

The `--skip-staleness-guard` flag remains the escape hatch for tests and
recovery flows. Phase 6 never invokes it; only operators do, after
diagnosing why the sentinel is stale.

## Ordering

The canonical Phase 6 ordering surrounding this step is:

```
default:branch-cleanup (70) →
project:finalize-step-deploy-target (80) →
project:finalize-step-sync-plugin-cache (85) →
default:record-metrics (990)
```

`order: 85` places this step immediately after
`project:finalize-step-deploy-target` (so the cache mirrors the
just-regenerated `target/claude/` content), post-`branch-cleanup` on the
main checkout. Executor regeneration is NOT a separate finalize step —
`integrate_into_main` (invoked during the move-back, before
`branch-cleanup`) is the single owner of executor regeneration against
main.

## Inputs

- `{plan_id}` — required. Used for logging.

## Execution

Inline-only — this step does NOT delegate to a Task agent. The sync
engine is a fast Python script with deterministic output.

### 1. Invoke the consolidated sync engine

```bash
python3 .claude/skills/sync-plugin-cache/scripts/sync.py
```

The script returns a TOON document with `status` (`success` |
`partial` | `error`), `synced_count`, `failed_count`,
`summary_message`, and a `synced[N]{bundle,version,status}` table.

### 2. Parse the result

| Field | Meaning |
|-------|---------|
| `status: success` | All bundles synced; record `outcome=done` and use `synced_count` for the display detail |
| `status: partial` | Some bundles failed; record `outcome=failed` and surface `summary_message` in `display_detail` |
| `status: error` | Hard failure (no bundles synced); record `outcome=failed` and surface `summary_message` |

### 3. Mark step complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step project:finalize-step-sync-plugin-cache \
  --outcome {done|failed} \
  --display-detail "{display_detail}"
```

On `status: success`, `{display_detail}` is `"{synced_count} bundles synced"`.
On `status: partial` or `status: error`, surface the engine's
`summary_message` field verbatim in `--display-detail` so the renderer
shows the underlying failure for triage.
