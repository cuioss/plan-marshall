---
name: default:coverage_check
description: Run coverage build and verify threshold
order: 30
---

# Coverage Check

Built-in verification step that runs the coverage build and verifies the coverage threshold from config.

## Dispatch

Resolved from the `default:` prefix by `phase-5-execute` via the Built-in Step Dispatch Table. Execution is inlined — no external skill is loaded.

**Whether this step fires is decided exclusively by `phase_5.verification_steps` in the per-plan execution manifest** (`manage-execution-manifest read`). This document carries **no embedded skip logic** — `coverage` runs iff `manage-execution-manifest`'s decision matrix included `coverage` in the manifest's `verification_steps` list. Any skip rule (e.g., docs-only plans, recipe paths, early-terminate analysis) is encoded in the matrix, not here.

Resolve via `architecture resolve --command coverage` and run the resolved executable. Threshold enforcement is native to the resolved build command: pytest emits `--cov-fail-under={threshold}` from `build.py::cmd_coverage`, and JaCoCo (Maven/Gradle) enforces the threshold via build-tool configuration. No secondary parse-and-check call is required.

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command coverage --module {module} --audit-plan-id {plan_id}
```

## Return Contract

Follows the standard phase-5-execute verification result shape: a coverage value below the configured threshold (or a failed build) surfaces as a non-zero exit and is routed through the Step 10 triage loop (fix-task creation, suppress, or accept) with `verification_max_iterations` from config.

## Related Steps

See the phase-5-execute SKILL.md **Built-in Step Dispatch Table** for the full set of default verify steps (`default:quality_check`, `default:build_verify`, `default:coverage_check`).
