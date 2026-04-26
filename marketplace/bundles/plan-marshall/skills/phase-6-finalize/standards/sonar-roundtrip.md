---
name: default:sonar-roundtrip
description: Sonar analysis roundtrip
order: 40
---

# Sonar Roundtrip

Pure executor for the `sonar-roundtrip` finalize step. Runs the Sonar quality gate check and (on findings) the loop-back-to-execute fix flow.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `sonar-roundtrip` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

## Timeout Contract

This step runs as a Task agent (`plan-marshall:sonar-roundtrip-agent`) under a **15-minute (900 s) per-agent timeout budget** enforced by the SKILL.md Step 3 dispatch loop. The budget covers the full roundtrip: gate fetch, issue triage, optional fix-task creation, and (on loop-back) the `manage-status transition --loop-back 5-execute` handoff.

**Graceful degradation**: When the wrapper expires:

1. The dispatcher logs an ERROR entry at `[ERROR] (plan-marshall:phase-6-finalize) Step default:sonar-roundtrip timed out after 900s — marking failed and continuing`.
2. The dispatcher marks this step `failed` via `manage-status mark-step-done … --outcome failed --display-detail "timed out after 900s"`.
3. The dispatcher continues with the next manifest step. Sonar timeouts MUST NOT block the rest of finalize — knowledge/lessons capture, branch cleanup, archive, and metrics still run.
4. On the next Phase 6 entry, the resumable re-entry check sees `outcome=failed` and retries this step from scratch (one fresh attempt per invocation).

There is no internal soft-timeout, polling cap, or partial-progress checkpoint inside this document — the wrapper is the only timeout authority.

## Inputs

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

**Branch C — Sonar not configured for project** (the dispatcher ran this step but the workflow-integration-sonar skill determined Sonar is not configured — e.g., no SonarQube/SonarCloud credentials, no project key):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \
  --display-detail "Sonar not configured"
```

Note: there is no "config disabled" branch — when the manifest excludes `sonar-roundtrip`, the dispatcher does not run this document at all, so no step record is written.
