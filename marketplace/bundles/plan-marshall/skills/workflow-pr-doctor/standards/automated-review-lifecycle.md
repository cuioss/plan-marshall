# Automated Review Lifecycle Reference

Detailed reference for the Automated Review Lifecycle mode used by phase-6-finalize when `decisions.automated_review: true`.

## Input Parameters

- `plan_id` — for logging and Q-Gate findings
- `pr_number` — PR number (from phase-6-finalize Step 4 or pr-view)
- `review_bot_buffer_seconds` — seconds to wait after CI for review bots (from config)

## Step-by-Step Reference

### Step 1: Wait for CI

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci wait \
  --pr-number {pr_number}
```

**Bash tool timeout**: 1800000ms (30-minute safety net). Internal timeout managed by script.

| Script Output | Action |
|--------------|--------|
| `final_status: success` | Proceed to step 2 |
| `final_status: failure` | Return `{status: ci_failure, details: ...}` for loop-back |
| `status: timeout` | Ask user (continue/skip/abort) |

### Step 2: Buffer for Review Bots

```bash
sleep {review_bot_buffer_seconds}
```

### Step 3: Fetch and Triage Comments

Follow the workflow-integration-ci "Handle Review" workflow with these additions:

1. **Fetch comments**: `fetch-comments --pr {pr_number} --unresolved-only`
2. **Batch triage**: `triage-batch --comments '[...]'`
3. **Process by action type** — see the CI skill's Handle Review workflow for the standard flow, with these lifecycle-specific overrides:

**code_change** — additionally persist as Q-Gate finding:
```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 6-finalize --source qgate \
  --type pr-comment --title "{comment summary}" \
  --detail "{comment body} at {path}:{line}"
```
Then reply acknowledging the finding.

**explain** and **ignore** — follow standard CI workflow (reply + resolve or resolve-only).

### Step 4: Return Summary

```toon
status: success
pr_number: {pr_number}
ci_status: success
comments_total: {N}
comments_unresolved: {N}
processed:
  code_changes: {N}
  explanations: {N}
  ignored: {N}
threads_resolved: {N}
loop_back_needed: {true|false}
findings_created: {N}
```

If `loop_back_needed == true`, phase-6-finalize creates fix tasks and loops back to phase-5-execute.

## Error Handling

| Failure | Action |
|---------|--------|
| CI wait returns failure | Return error with details; do not proceed to fetch |
| fetch-comments returns empty | Report "No unresolved comments" and return success |
| triage/reply/resolve failure | Log warning, continue — best-effort processing |
