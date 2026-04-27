---
name: default:quality_check
description: Run quality-gate build command
order: 10
---

# Quality Check

Built-in verification step that runs the project's quality-gate build command for code quality checks (lint, formatting, static analysis, etc.).

## Dispatch

Resolved from the `default:` prefix by `phase-5-execute` via the Built-in Step Dispatch Table. Execution is inlined — no external skill is loaded.

**Whether this step fires is decided exclusively by `phase_5.verification_steps` in the per-plan execution manifest** (`manage-execution-manifest read`). This document carries **no embedded skip logic** — `quality-gate` runs iff `manage-execution-manifest`'s decision matrix included `quality-gate` in the manifest's `verification_steps` list. Any skip rule (e.g., docs-only plans, recipe paths, early-terminate analysis) is encoded in the matrix, not here.

Resolve the command via:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command quality-gate --module {module} --trace-plan-id {plan_id}
```

Run the returned `executable` as the verification command for the task.

## Return Contract

Follows the standard phase-5-execute verification result shape: a non-zero exit code or findings in the build log surface as failures and are routed through the Step 10 triage loop (fix-task creation, suppress, or accept) with `verification_max_iterations` from config.

## Related Steps

See the phase-5-execute SKILL.md **Built-in Step Dispatch Table** for the full set of default verify steps (`default:quality_check`, `default:build_verify`, `default:coverage_check`).
