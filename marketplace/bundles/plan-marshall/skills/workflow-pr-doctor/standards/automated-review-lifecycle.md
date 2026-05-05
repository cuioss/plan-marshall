# Automated Review Lifecycle Reference

Detailed reference for the Automated Review Lifecycle mode used by phase-6-finalize when `decisions.automated_review: true`.

## Input Parameters

- `plan_id` — for logging, finding storage, and Q-Gate findings
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
| `status: success`, `timed_out: true` | No new comment within timeout — proceed to Step 3 anyway (the producer at Step 3 surfaces whatever is on the PR; if nothing, the lifecycle returns `comments_total: 0`) |
| `status: error` | Treat as warning, log, proceed to Step 3 best-effort |

### Step 3: Producer-stage PR comments as findings

Call the producer-side comments-stage subcommand once. It fetches PR review comments, applies pre-filters (resolved threads, plan author's own replies, etc.), and writes one `pr-comment` finding per surviving comment into the per-plan findings store. The producer is the ONLY surface that fetches and stores `pr-comment` findings — this lifecycle does NOT classify or decide on comments inline.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
  comments-stage --pr-number {pr_number} --plan-id {plan_id}
```

For GitLab projects use `plan-marshall:workflow-integration-gitlab:gitlab_pr comments-stage` instead. Provider selection follows `manage-providers` for the plan's host.

### Step 4: Enumerate pending pr-comment findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings query \
  --plan-id {plan_id} --type pr-comment --resolution pending
```

If the result's `findings` list is empty, return success with `comments_total: 0` and `loop_back_needed: false`.

### Step 5: Per-finding dispatch through ext-triage-{domain}

For each pending finding, perform the following sequence sequentially. The classifier-as-decision-authority pattern (a single keyword classifier deciding `code_change` / `explain` / `ignore` for a whole batch) is RETIRED — every per-finding decision now goes through the loaded `ext-triage-{domain}` skill's standards.

1. **Detect domain** via `architecture which-module --path {finding.file_path}`.
2. **Resolve the triage extension** via `manage-config resolve-workflow-skill-extension --domain {domain} --type triage`.
3. **Load the resolved extension** with `Skill: {bundle}:ext-triage-{domain}`. The extension brings its `severity.md`, `suppression.md`, and `pr-comment-disposition.md` into context.
4. **Decide** per the loaded `pr-comment-disposition.md` table:

   | Decision | Action |
   |----------|--------|
   | **FIX** | Create a fix task (prepare-add → commit-add) and loop back to phase-5-execute |
   | **SUPPRESS** | Apply domain-specific annotation (per loaded `suppression.md`); reply on the thread acknowledging the suppression; resolve the thread |
   | **ACCEPT** | Reply on the thread with rationale; resolve the thread |
   | **AskUserQuestion** | Ask the user (one question per finding, never batched) when the loaded standards leave the call genuinely ambiguous |

5. **Resolve the finding** via `manage-findings resolve --hash-id {hash_id} --resolution {fixed|suppressed|accepted|taken_into_account} --detail "{rationale}"`.

The PR thread reply / resolve calls use `plan-marshall:tools-integration-ci:ci pr prepare-comment` → `pr thread-reply` → `pr resolve-thread` (see the canonical phase-6-finalize `automated-review.md` standard for the exact command sequences).

### Step 6: Return Summary

```toon
status: success
pr_number: {pr_number}
ci_status: success
comments_total: {N}
comments_unresolved: {N}
processed:
  fixed: {N}
  suppressed: {N}
  accepted: {N}
  taken_into_account: {N}
threads_resolved: {N}
loop_back_needed: {true|false}
```

`loop_back_needed` is `true` when at least one finding resolved to `fixed` (and therefore produced a fix task). When it is `true`, phase-6-finalize creates the fix tasks and loops back to phase-5-execute.

## Error Handling

| Failure | Action |
|---------|--------|
| CI wait returns failure | Return error with details; do not proceed to producer-stage |
| `comments-stage` returns empty | Report "No unresolved comments" via the Step 4 query (which will also return empty) and return success |
| `manage-findings query` fails | Log error, return error to caller |
| Per-finding triage step (resolve, reply, thread-resolve) fails | Log warning, continue with the next finding — best-effort processing; the failed finding remains `pending` and is retried on the next finalize entry |
