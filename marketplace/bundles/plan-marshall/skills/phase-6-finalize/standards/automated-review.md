---
name: default:automated-review
description: CI automated review
order: 30
---

# Automated Review

Pure executor for the `automated-review` finalize step. Waits for CI, handles review bot comments, and resolves or loops back on findings.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `automated-review` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

## Timeout Contract

This step runs as a Task agent (`plan-marshall:automated-review-agent`) under a **15-minute (900 s) per-agent timeout budget** enforced by the SKILL.md Step 3 dispatch loop. The budget covers the full sequence: CI wait, review-bot buffer, comment fetching, triage, thread replies, and thread resolution.

**Graceful degradation**: When the wrapper expires:

1. The dispatcher logs an ERROR entry at `[ERROR] (plan-marshall:phase-6-finalize) Step default:automated-review timed out after 900s — marking failed and continuing`.
2. The dispatcher marks this step `failed` via `manage-status mark-step-done … --outcome failed --display-detail "timed out after 900s"`.
3. The dispatcher continues with the next manifest step. The pipeline does NOT abort; later steps still run.
4. On the next Phase 6 entry, the resumable re-entry check sees `outcome=failed` and retries this step from scratch (one fresh attempt per invocation).

There is no internal soft-timeout, polling cap, or partial-progress checkpoint inside this document — the wrapper is the only timeout authority. Standards-internal commands (CI wait, `pr wait-for-comments`) carry their own short polling intervals but never their own outer ceiling.

## Inputs

- A PR exists (from `create-pr` earlier in the manifest list, or pre-existing on the branch)
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All `ci` script invocations below MUST pass `--project-dir {worktree_path}`.

## Execution

### Get PR number

Use the `pr_number` from the create-pr step. If not available:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr view
```

Read `pr_number` from the TOON output. If `ci pr view` returns `status: error` (no PR exists for the branch), the underlying workflow returns immediately with no comments to process — the step still records `done` with a `display_detail` that reflects "no PR available" rather than re-entering the skip-logic anti-pattern.

### Load and execute automated review workflow

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:workflow-integration-github"
```

```
Skill: plan-marshall:workflow-integration-github
```

Execute **Workflow 3: Automated Review Lifecycle** with:
- `plan_id`: from context
- `pr_number`: from above
- `review_bot_buffer_seconds`: from phase-6-finalize config (default: 180; max-wait ceiling for the polling `pr wait-for-comments` step)
- `worktree_path`: `{worktree_path}` resolved at finalize entry (forwarded to all ci/github subprocess calls)

The workflow handles CI wait, review bot buffer, comment fetching, triage, thread replies, and thread resolution.

### Handle findings (loop-back)

**On findings** (review comments requiring code changes, `loop_back_needed == true`):

1. Create fix tasks:
```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks add \
  --plan-id {plan_id} --title "Fix: {comment summary}" --domain {domain} --profile implementation \
  --deliverable 0
```

2. Loop back to phase-5-execute (iteration + 1):
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
  --plan-id {plan_id} --loop-back 5-execute
```

3. Continue until clean or max iterations (3).

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. Mark done only on the terminal pass that returns clean (or on a skip); loop-back iterations do not terminate the step.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the review outcome. The payload differs by branch:

**Branch A — terminal clean pass** (no loop-back needed): `{N}` is the count of review comments resolved in the final pass (from the `workflow-integration-github` return payload, e.g. `comments_resolved`).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome done \
  --display-detail "{N} comment(s) resolved (no loop-back)"
```

**Branch B — no PR available** (the dispatcher ran this step but no PR exists for the branch — the underlying workflow returned immediately with no comments to process):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome done \
  --display-detail "no PR available"
```

**Branch C — loop-back recorded** (intermediate pass; used only when a non-terminal iteration must be surfaced in the output): `{iteration}` is the current loop-back iteration number (1..3). This branch is informational — the terminal pass still uses Branch A when review eventually goes clean.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome done \
  --display-detail "loop-back iteration {iteration}"
```
