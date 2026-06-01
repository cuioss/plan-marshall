---
name: finalize-step-plugin-doctor
description: Finalize-phase wrapper that runs plugin-doctor against skills touched by the plan, reading modified_files from references.json and passing skill paths directly via --paths
user-invocable: false
allowed-tools: Bash
order: 65
---

# Finalize Step: plugin-doctor

## Purpose

Validate plugin architecture (enforcement-block structure, standards registration, description lengths, registration convention) for any skill the plan modifies, before the plugin cache is synced. Catches structural breakage that quality-gate (ruff/mypy/pytest) cannot detect. Runs before `finalize-step-sync-plugin-cache` so violations abort finalize without polluting the host-global cache.

When the plan runs in an isolated worktree, the scan first regenerates a worktree-bound executor so the `manage-invocation-invalid` rule probes each script's `--help` against the worktree's TRUE argparse surface. Without this step, the worktree's `.plan/execute-script.py` is a symlink to the main checkout's executor, whose embedded mappings resolve every `manage-*` notation to the main-checkout (pre-plan) script — making a newly added subcommand read as a false-positive "unregistered" and a newly required flag read as a false-negative that masks the real CI finding.

## Interface Contract

Invoked by `plan-marshall:phase-6-finalize` for projects that include `project:finalize-step-plugin-doctor` in their `phase-6-finalize.steps` list.

Accepts the standard finalize-step arguments:

- `--plan-id` — plan identifier (required, used to query references.json for modified_files)
- `--iteration` — finalize iteration counter (accepted for contract compliance, no effect)

MUST be ordered **before** `project:finalize-step-sync-plugin-cache` in the steps list.

In a worktree-backed plan, the scan step is preceded by a worktree-fresh-executor regeneration (Step 4 below) that rebinds notation→path resolution to the worktree's scripts. Regeneration failure is non-fatal (logged WARN) — a scan against the still-stale executor is no worse than not regenerating, so finalize must not hard-block on a mapping refresh.

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

If zero skill paths remain after filtering, log, record the step as done, and return success:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (project:finalize-step-plugin-doctor) No skill changes detected; skipping plugin-doctor scan"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-plugin-doctor --outcome done \
  --display-detail "no skill changes detected"
```

### Step 4: Regenerate a worktree-fresh executor

Resolve the active worktree path:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-worktree-path \
  --plan-id {plan_id}
```

Parse `worktree_path` from the returned TOON. If it is empty, the plan runs against the main checkout — the executor already reflects the current checkout, so skip regeneration and proceed to Step 5.

When `worktree_path` is non-empty, replace the worktree's `.plan/execute-script.py` symlink (which points at the main-checkout executor) with a worktree-bound executor so the `manage-invocation-invalid` rule probes `--help` against the worktree's argparse:

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate \
  --marketplace-root {worktree_path}
```

This mirrors `test/conftest.py::_ensure_executor_present` on CI. Regeneration failure is **non-fatal**: log a WARN line and proceed to Step 5 with the existing executor.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[STATUS] (project:finalize-step-plugin-doctor) Worktree executor regeneration failed; scanning against existing executor"
```

### Step 5: Invoke plugin-doctor

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace \
  scan --paths {space-separated skill directory paths}
```

On non-zero exit code or any rule violation in the output, log the failure, record the step outcome, and exit with status: error so phase-6-finalize aborts before the next step:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-plugin-doctor --outcome failed \
  --display-detail "plugin-doctor: {N} violations"
```

On success, log, record the step as done, and exit success:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-plugin-doctor --outcome done \
  --display-detail "plugin-doctor clean: {N} skills scanned"
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Missing `pm-plugin-development` bundle | Fatal config error — the project opted into the wrapper without the dependency |
| Empty `worktree_path` (main-checkout flow) | Skip Step 4 regeneration — the executor already reflects the current checkout; proceed to the scan |
| Worktree executor regeneration fails | Non-fatal — log WARN and scan against the existing executor; finalize does not hard-block on a mapping refresh |
| Empty modified_files | Skip-clean exit — record `mark-step-done --outcome done --display-detail "no skill changes detected"` so the `phase_steps_complete` handshake invariant counts the step as done |
| plugin-doctor rule violations | Fatal — record `mark-step-done --outcome failed --display-detail "plugin-doctor: {N} violations"`, then abort finalize before the next step |
| plugin-doctor clean | Record `mark-step-done --outcome done --display-detail "plugin-doctor clean: {N} skills scanned"` |

## Related

- [.claude/skills/finalize-step-sync-plugin-cache/SKILL.md](../finalize-step-sync-plugin-cache/SKILL.md) — sibling pattern for cache sync
- `pm-plugin-development:plugin-doctor` — underlying scan tool with `--paths` support
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md) — finalize phase that invokes this wrapper
