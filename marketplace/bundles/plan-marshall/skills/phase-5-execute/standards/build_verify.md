---
name: default:build_verify
description: Run full test suite
order: 20
role: module-tests
---

# Build Verify

Built-in verification step that runs the full test suite to verify the build.

## Dispatch

Resolved from the `default:` prefix by `phase-5-execute` via the Built-in Step Dispatch Table. Execution is inlined — no external skill is loaded.

**Whether this step fires is decided exclusively by `phase_5.verification_steps` in the per-plan execution manifest** (`manage-execution-manifest read`). This document carries **no embedded skip logic** — `module-tests` / `verify` runs iff `manage-execution-manifest`'s decision matrix included it in the manifest's `verification_steps` list. Any skip rule (e.g., docs-only plans, recipe paths, early-terminate analysis) is encoded in the matrix, not here.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

Resolve the command via:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command verify --module {module} --audit-plan-id {plan_id}
```

Run the returned `executable` as the verification command for the task.

## Return Contract

Follows the standard phase-5-execute verification result shape: a non-zero exit code or test failures in the build log surface as failures and are routed through the Step 10 triage loop (fix-task creation, suppress, or accept) with `max_iterations` from config.

## Related Steps

See the phase-5-execute SKILL.md **Built-in Step Dispatch Table** for the full set of default verify steps (`default:quality_check`, `default:build_verify`, `default:coverage_check`).
