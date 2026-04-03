---
name: ref-manage-contract
description: Shared contract for all manage-* skills covering enforcement rules, TOON output format, error responses, and plan directory layout
user-invocable: false
---

# Manage-* Skills Shared Contract

**REFERENCE MODE**: Shared contract that all manage-* skills follow. Loaded by manage-* skills to avoid repeating identical sections.

## Enforcement Contract

All manage-* skills follow these rules:

**Execution mode**: Run scripts via the executor; parse TOON output for status and route accordingly.

```
python3 .plan/execute-script.py plan-marshall:{skill}:{script} {command} {args}
```

**Prohibited actions:**
- Do not modify managed files directly; all mutations go through the script API
- Do not invent script arguments not listed in the skill's Operations section
- Do not bypass the executor to call scripts directly

**Constraints:**
- Scripts are invoked only through `python3 .plan/execute-script.py` with 3-part notation
- Scripts that are imported as Python modules by other scripts use underscores in filenames (e.g., `manage_status.py`, `run_config.py`)
- All script output uses TOON format (see `plan-marshall:ref-toon-format` for full specification)

## TOON Output Contract

All manage-* scripts return TOON-formatted output (see `plan-marshall:ref-toon-format` for the TOON specification).

### Success Response

```toon
status: success
message: {description of what was done}
{skill-specific fields}
```

### Error Response

```toon
status: error
error: {error_code}
message: {human-readable description}
```

Exit codes: `0` = success, `1` = error.

Common error codes across all manage-* skills:

| Error Code | Cause |
|------------|-------|
| `not_found` | Requested resource does not exist |
| `already_exists` | Resource already exists (create conflict) |
| `invalid_argument` | Invalid argument value |
| `missing_argument` | Required argument not provided |
| `validation_error` | Data failed validation |

## Plan Directory Layout

Plan-scoped manage-* skills store data under `.plan/plans/{plan_id}/`:

```
.plan/
  plans/
    {plan_id}/
      status.json          # manage-status
      references.json      # manage-references
      request.md           # manage-plan-documents
      solution_outline.md  # manage-solution-outline
      artifacts/
        findings.jsonl     # manage-findings (plan)
        assessments.jsonl  # manage-findings (assessments)
        qgate-{phase}.jsonl # manage-findings (Q-Gate)
      tasks/
        TASK-001.json      # manage-tasks
      logs/
        script-execution.log  # manage-logging
        work.log              # manage-logging
        decision.log          # manage-logging
      work/
        metrics.toon       # manage-metrics
        metrics.md         # manage-metrics
```

Global-scoped skills store data under `.plan/` directly:

```
.plan/
  marshal.json             # manage-config
  run-configuration.json   # manage-run-config
  memories/                # manage-memories
  lessons-learned/         # manage-lessons
  logs/                    # manage-logging (global)
```

## Scope Model

| Scope | Description | Storage Root |
|-------|-------------|-------------|
| `plan` | Data tied to a specific plan_id | `.plan/plans/{plan_id}/` |
| `global` | Data shared across all plans | `.plan/` |
| `hybrid` | Both plan-scoped and global operations | Both |
