# Automated Review Lifecycle Reference

Detailed reference for the Automated Review Lifecycle mode used by phase-6-finalize when `decisions.automated_review: true`.

## Input Parameters

- `plan_id` — for logging and Q-Gate findings
- `pr_number` — PR number (from phase-6-finalize Step 4 or pr-view)
- `review_bot_buffer_seconds` — max-wait ceiling (in seconds) passed to `pr wait-for-comments` as `--timeout`. The polling subcommand exits as soon as a new review-bot comment is posted, so this is a cap, not a fixed delay. Sourced from phase-6-finalize config (default: 180).

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

### Step 2: Wait for Review Bot Comments

Poll for new review-bot comments using the dedicated CI subcommand. This replaces a previous bash `sleep` (blocked by the Claude Code harness for long leading durations) and exits as soon as a new comment arrives instead of always sleeping the full window.

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr wait-for-comments \
  --pr-number {pr_number} --timeout {review_bot_buffer_seconds}
```

| Script Output | Action |
|--------------|--------|
| `status: success`, `timed_out: false` | New comment(s) detected — proceed to Step 3 |
| `status: success`, `timed_out: true` | No new comment within timeout — proceed to Step 3 anyway (the subsequent `fetch-comments` call surfaces whatever is on the PR; if nothing, the lifecycle returns `comments_total: 0`) |
| `status: error` | Treat as warning, log, proceed to Step 3 best-effort |

### Step 3: Fetch and Triage Comments

Follow the workflow-integration-github "Handle Review" workflow with these additions:

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
