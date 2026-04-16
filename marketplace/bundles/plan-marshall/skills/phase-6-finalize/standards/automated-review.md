# Automated Review

Wait for CI, handle review bot comments, and resolve or loop-back on findings.

## Prerequisites

- Config field `3_automated_review` is `true`
- A PR exists (from create-pr step or pre-existing)
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All `ci` script invocations below MUST pass `--project-dir {worktree_path}`.

## Execution

### Get PR number

Use the `pr_number` from the create-pr step. If not available:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr view
```

Read `pr_number` from the TOON output. If no PR exists, skip automated review.

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

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome done
```
