---
name: default:build_verify
description: Run full test suite
order: 20
---

# Build Verify

Built-in verification step that runs the full test suite to verify the build.

## Dispatch

Resolved from the `default:` prefix by `phase-5-execute` via the Built-in Step Dispatch Table. Execution is inlined — no external skill is loaded.

**Whether this step fires is decided exclusively by `phase_5.verification_steps` in the per-plan execution manifest** (`manage-execution-manifest read`). This document carries **no embedded skip logic** — `module-tests` / `verify` runs iff `manage-execution-manifest`'s decision matrix included it in the manifest's `verification_steps` list. Any skip rule (e.g., docs-only plans, recipe paths, early-terminate analysis) is encoded in the matrix, not here.

Resolve the command via:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command verify --name {module} --trace-plan-id {plan_id}
```

Run the returned `executable` as the verification command for the task.

## Return Contract

Follows the standard phase-5-execute verification result shape: a non-zero exit code or test failures in the build log surface as failures and are routed through the Step 10 triage loop (fix-task creation, suppress, or accept) with `verification_max_iterations` from config.

## Related Steps

See the phase-5-execute SKILL.md **Built-in Step Dispatch Table** for the full set of default verify steps (`default:quality_check`, `default:build_verify`, `default:coverage_check`).
