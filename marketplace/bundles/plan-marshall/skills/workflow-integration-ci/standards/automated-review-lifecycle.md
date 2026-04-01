# Automated Review Lifecycle Reference

Detailed reference for Workflow 3 (Automated Review Lifecycle) used by phase-6-finalize when `3_automated_review == true`.

## Input Parameters

- `plan_id` — for logging and Q-Gate findings
- `pr_number` — PR number (from phase-6-finalize Step 4 or pr-view)
- `review_bot_buffer_seconds` — seconds to wait after CI for review bots (from config)

## GitHub GraphQL ID Format Rules

When calling CI integration scripts, use the correct ID format:

| Operation | Parameter | ID Field | Format Example |
|-----------|-----------|----------|----------------|
| `thread-reply --thread-id` | Comment's `id` field | GraphQL node ID | `PRRC_kwDO...` |
| `resolve-thread --thread-id` | Comment's `thread_id` field | GraphQL node ID | `PRRT_kwDO...` |

**NEVER use numeric IDs** — GitHub GraphQL requires global node IDs.

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

### Step 3: Fetch Comments

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr fetch-comments --pr {pr_number} --unresolved-only
```

### Step 4: Triage Each Comment

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr triage --comment '{comment_json}'
```

### Step 5: Process by Action Type

**code_change** (requires implementation):
- Persist as Q-Gate finding:
  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
    qgate add --plan-id {plan_id} --phase 6-finalize --source qgate \
    --type pr-comment --title "{comment summary}" \
    --detail "{comment body} at {path}:{line}"
  ```
- Reply acknowledging:
  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr thread-reply \
      --pr-number {pr_number} --thread-id {comment_id} --body "Acknowledged — creating fix task."
  ```

**explain** (reply with explanation):
- Generate explanation based on code context
- Reply to thread:
  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr thread-reply \
      --pr-number {pr_number} --thread-id {comment_id} --body "{explanation}"
  ```
- Resolve thread:
  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr resolve-thread \
      --pr-number {pr_number} --thread-id {thread_id}
  ```

**ignore** (dismiss):
- Resolve thread:
  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr resolve-thread \
      --pr-number {pr_number} --thread-id {thread_id}
  ```

### Step 6: Return Summary

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
| CI router returns `status: failure` | Return error with stderr details; do not proceed to fetch |
| fetch-comments returns empty | Report "No unresolved comments" and return success |
| triage returns `status: failure` | Log warning, skip comment, continue with remaining |
| thread-reply fails | Log warning, continue — reply is best-effort |
| resolve-thread fails | Log warning, continue — resolution is best-effort |
