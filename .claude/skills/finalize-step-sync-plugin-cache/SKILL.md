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

## Ordering

The canonical Phase 6 ordering surrounding this step is:

```
default:branch-cleanup (70) →
project:finalize-step-deploy-target (80) →
project:finalize-step-sync-plugin-cache (85) →
project:finalize-step-regenerate-executor (90) →
default:record-metrics (990)
```

`order: 85` places this step immediately after
`project:finalize-step-deploy-target` (so the cache mirrors the
just-regenerated `target/claude/` content) and before
`project:finalize-step-regenerate-executor` (which scans the freshly
synced cache), both post-`branch-cleanup` on the main checkout.

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
