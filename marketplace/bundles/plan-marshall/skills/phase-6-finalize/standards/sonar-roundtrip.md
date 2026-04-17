# Sonar Roundtrip

Sonar quality gate check and issue resolution.

## Prerequisites

- Config field `4_sonar_roundtrip` is `true`
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). The Sonar workflow below forwards `--project-dir {worktree_path}` to every sonar/build subprocess it spawns.

## Execution

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:workflow-integration-sonar"
```

```
Skill: plan-marshall:workflow-integration-sonar
  Arguments: --project-dir {worktree_path}
```

Handles Sonar quality gate and issue resolution. On findings, follows the same loop-back pattern as automated review:

1. Create fix tasks for Sonar issues
2. Loop back to phase-5-execute via `manage-status transition --loop-back 5-execute`
3. Continue until clean or max iterations (3)

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. Mark done only on the terminal pass that returns clean (or on a skip); loop-back iterations do not terminate the step.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the Sonar quality gate result. The payload differs by branch:

**Branch A — quality gate passed** (terminal Sonar pass returns clean):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \
  --display-detail "quality gate passed"
```

**Branch B — quality gate failed** (gate stayed red after max loop-back iterations; the step still marks `done` because the handshake records that the workflow executed — remediation is deferred to human follow-up):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \
  --display-detail "quality gate failed"
```

**Branch C — skipped** (config `4_sonar_roundtrip` is `false`, or the workflow-integration-sonar skill determined Sonar is not configured for this project):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \
  --display-detail "skipped"
```
