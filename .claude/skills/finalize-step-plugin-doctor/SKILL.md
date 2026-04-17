---
name: finalize-step-plugin-doctor
description: Finalize-phase wrapper that runs plugin-doctor against skills touched by the plan, reading modified_files from references.json and passing skill paths directly via --paths
user-invocable: false
allowed-tools: Bash
order: 85
---

# Finalize Step: plugin-doctor

## Purpose

Validate plugin architecture (enforcement-block structure, standards registration, description lengths, registration convention) for any skill the plan modifies, before the plugin cache is synced. Catches structural breakage that quality-gate (ruff/mypy/pytest) cannot detect. Runs before `finalize-step-sync-plugin-cache` so violations abort finalize without polluting the host-global cache.

## Interface Contract

Invoked by `plan-marshall:phase-6-finalize` for projects that include `project:finalize-step-plugin-doctor` in their `phase-6-finalize.steps` list.

Accepts the standard finalize-step arguments:

- `--plan-id` — plan identifier (required, used to query references.json for modified_files)
- `--iteration` — finalize iteration counter (accepted for contract compliance, no effect)

MUST be ordered **before** `project:finalize-step-sync-plugin-cache` in the steps list.

## Workflow

### Step 1: Read modified files

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field modified_files
```

Parse the returned list of file paths.

### Step 2: Extract skill directory paths

Filter the file list to entries matching either pattern:
- `marketplace/bundles/{bundle}/skills/{skill}/` (marketplace skills)
- `.claude/skills/{skill}/` (project-local skills)

For each matching file, extract the skill directory path (everything up to and including the skill name directory). Deduplicate the result.

Example: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` → `marketplace/bundles/plan-marshall/skills/phase-5-execute`

### Step 3: Skip-clean exit

If zero skill paths remain after filtering, log and return success:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (project:finalize-step-plugin-doctor) No skill changes detected; skipping plugin-doctor scan"
```

### Step 4: Invoke plugin-doctor

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace \
  scan --paths {space-separated skill directory paths}
```

On non-zero exit code or any rule violation in the output, log the failure and exit with status: error so phase-6-finalize aborts before the next step.

On success, log and exit success.

## Error Handling

| Scenario | Action |
|----------|--------|
| Missing `pm-plugin-development` bundle | Fatal config error — the project opted into the wrapper without the dependency |
| Empty modified_files | Skip-clean exit (no work to do) |
| plugin-doctor rule violations | Fatal — verification step, violations must block finalize |

## Related

- [.claude/skills/finalize-step-sync-plugin-cache/SKILL.md](../finalize-step-sync-plugin-cache/SKILL.md) — sibling pattern for cache sync
- `pm-plugin-development:plugin-doctor` — underlying scan tool with `--paths` support
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md) — finalize phase that invokes this wrapper
