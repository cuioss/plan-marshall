# Automated Review

Wait for CI, handle review bot comments, and resolve or loop-back on findings.

## Prerequisites

- Config field `3_automated_review` is `true`
- A PR exists (from create-pr step or pre-existing)

## Execution

### Get PR number

Use the `pr_number` from the create-pr step. If not available:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view
```

Read `pr_number` from the TOON output. If no PR exists, skip automated review.

### Load and execute automated review workflow

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:workflow-integration-ci"
```

```
Skill: plan-marshall:workflow-integration-ci
```

Execute **Workflow 3: Automated Review Lifecycle** with:
- `plan_id`: from context
- `pr_number`: from above
- `review_bot_buffer_seconds`: from phase-6-finalize config (default: 300)

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
python3 .plan/execute-script.py plan-marshall:manage-lifecycle:manage-lifecycle transition \
  --plan-id {plan_id} --loop-back 5-execute
```

3. Continue until clean or max iterations (3).
