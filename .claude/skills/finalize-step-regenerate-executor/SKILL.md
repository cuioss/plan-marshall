---
name: finalize-step-regenerate-executor
description: Finalize-phase wrapper that regenerates .plan/execute-script.py whenever a plan touched marketplace script files, so newly added notations resolve after merge
user-invocable: false
allowed-tools: Bash
order: 7
---

# Finalize Step: regenerate-executor

## Purpose

Close the executor-drift gap that causes newly added scripts under `marketplace/bundles/**/skills/**/scripts/` to resolve as `Unknown notation` after merge. The executor (`.plan/execute-script.py`) embeds a static mapping table generated from the plugin cache; neither `phase-6-finalize` nor `/sync-plugin-cache` triggered regeneration, so any plan that shipped a new script produced unresolvable canonical notations until a human ran `/marshall-steward` separately.

This wrapper runs right after `project:finalize-step-sync-plugin-cache` so the cache already reflects the merged source, then invokes the existing non-interactive `generate_executor generate` entrypoint when the plan's `modified_files` include any `.py` file under `marketplace/bundles/*/skills/*/scripts/`. Idempotent, non-fatal on failure — finalize must never block on a mapping refresh.

## Interface Contract

Invoked by `plan-marshall:phase-6-finalize` for projects that include `project:finalize-step-regenerate-executor` in their `phase-6-finalize.steps` list.

Accepts the standard finalize-step arguments:

- `--plan-id` — plan identifier (required, used to query references.json for modified_files)
- `--iteration` — finalize iteration counter (accepted for contract compliance, no effect)

MUST be ordered **after** `project:finalize-step-sync-plugin-cache` in the steps list — the generator scans the plugin cache and will miss newly added scripts if the cache is stale at regeneration time.

## Workflow

### Step 1: Read modified files

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field modified_files
```

Parse the returned list of file paths.

### Step 2: Filter for marketplace script additions

Filter the file list to entries matching the regex:

```
^marketplace/bundles/[^/]+/skills/[^/]+/scripts/[^/]+\.py$
```

Only `.py` files directly under `skills/*/scripts/` qualify. Nested subdirectories (e.g. `script-shared/scripts/build/`) are intentionally excluded from the filter — they contain importable modules rather than new user-facing notations, and are already covered by `_ALL_SCRIPT_DIRS` at PYTHONPATH level.

Deduplicate the result.

### Step 3: Skip-clean exit

If zero script paths remain after filtering, log and return success:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (project:finalize-step-regenerate-executor) No marketplace script changes detected; skipping executor regeneration"
```

### Step 4: Invoke generator

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate
```

Parse the returned TOON:

- `status: success` → log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (project:finalize-step-regenerate-executor) Executor regenerated: {script_count} scripts mapped"
```

- `status: error` or non-zero exit → log WARN and exit success (non-fatal, matching `finalize-step-sync-plugin-cache`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARN \
  --message "[WARN] (project:finalize-step-regenerate-executor) Executor regeneration failed — run /marshall-steward manually to recover"
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Empty `modified_files` | Skip-clean exit (no work to do) |
| No script additions in `modified_files` | Skip-clean exit |
| Generator returns `status: error` | Log `[WARN]`, exit success — finalize must not block on mapping drift |
| Generator raises unhandled exception | Same as above — non-fatal |

## Related

- [.claude/skills/finalize-step-sync-plugin-cache/SKILL.md](../finalize-step-sync-plugin-cache/SKILL.md) — sibling pattern, must run before this step
- [.claude/skills/finalize-step-plugin-doctor/SKILL.md](../finalize-step-plugin-doctor/SKILL.md) — earlier sibling (order 85) that validates skills before cache sync
- `plan-marshall:tools-script-executor:generate_executor` — underlying generator with the `generate` subcommand
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md) — finalize phase that dispatches this wrapper
