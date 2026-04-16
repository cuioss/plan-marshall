# Record Metrics

Generate and record the final plan metrics report before the plan is archived.

**CRITICAL**: `default:record-metrics` MUST immediately precede `default:archive-plan` in the pipeline. `manage-metrics generate` writes `metrics.md` inside `.plan/plans/{plan_id}/`, and `default:archive-plan` moves that directory to `.plan/archived-plans/{date}-{plan_id}/`. If archive runs first, metrics generation has no target directory and the final report is lost.

## Generate Final Metrics Report

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics generate \
  --plan-id {plan_id}
```

Capture the following fields from the returned TOON for the parent skill's output contract:

- `total_duration_seconds`
- `total_tokens`
- `file` (relative path to `metrics.md`)

## Display Consolidated Step-Outcome Summary

Read the plan status to retrieve step outcomes for the finalize phase:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
  --plan-id {plan_id}
```

Extract `metadata.phase_steps["6-finalize"]` from the response. This is a map of step names to outcomes (`done` or `skipped`).

Cross-reference against the configured `steps` list (already read during phase-6-finalize Step 2). For each configured step, look up its outcome in `phase_steps`. Steps not yet recorded (e.g., `record-metrics` itself, `archive-plan`) should show `pending` since they have not yet called `mark-step-done` at this point in the pipeline.

Display a consolidated table:

```
## Finalize Step Outcomes

| Step | Outcome |
|------|---------|
| commit-push | done |
| create-pr | done |
| automated-review | skipped |
| sonar-roundtrip | skipped |
| knowledge-capture | done |
| lessons-capture | done |
| branch-cleanup | done |
| record-metrics | pending |
| archive-plan | pending |
```

The table rows follow the order from the configured `steps` list. The `Outcome` column shows the value from `phase_steps` (`done`, `skipped`, or `failed`) or `pending` if no entry exists yet.

## Verify Observable End-State

After the step-outcome table, verify and display the observable end-state so the user can confirm the plan completed as expected without needing to ask follow-up questions.

**PR state** (only if `default:create-pr` is in the configured `steps` list):

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  pr view --project-dir {worktree_path_or_main_checkout}
```

Extract `state` (merged, open, closed) and `number` from the response. If the CI script returns an error (e.g., no PR exists), display `n/a`.

**Current branch and git status** (use `{main_checkout}` since worktree may already be removed by `branch-cleanup`):

```bash
git -C {main_checkout} branch --show-current
```

```bash
git -C {main_checkout} status --porcelain
```

**Worktree status** (only if the plan used a worktree): Check whether the worktree directory still exists. If `branch-cleanup` ran successfully, the worktree should be removed.

Display the end-state summary:

```
## End-State Verification

| Check | Status |
|-------|--------|
| PR | #{pr_number} {state} |
| Branch | {current_branch} |
| Working tree | {clean / N uncommitted files} |
| Worktree | {removed / still present at {path}} |
```

If any check reveals an unexpected state (e.g., PR still open when branch-cleanup marked done, uncommitted files present), log a warning:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARN --message "[VERIFY] (plan-marshall:phase-6-finalize:record-metrics) Unexpected end-state: {description}"
```

## Display Plan Completion Summary

Display the plan completion summary including core metrics:

```
## Plan Complete: {plan_id}

| Metric | Value |
|--------|-------|
| Total Duration | {formatted total_duration from metrics} |
| Total Tokens | {total_tokens from metrics} |
| PR | #{pr_number} {state} |
| Metrics | .plan/archived-plans/{date}-{plan_id}/metrics.md |
```

## Log Artifact

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:phase-6-finalize:record-metrics) metrics.md generated — {total_tokens} tokens, {total_duration_seconds}s"
```

## Error Handling

If `manage-metrics generate` returns a non-success status, log the error to work.log and continue — metrics recording must never block the archive step.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize:record-metrics) metrics generate failed — {error_message}"
```

## Output Contract

This step populates the following fields in the parent skill's `metrics` output block:

| Field | Source |
|-------|--------|
| `metrics.total_duration_seconds` | `total_duration_seconds` from generate output |
| `metrics.total_tokens` | `total_tokens` from generate output |
| `metrics.metrics_file` | `.plan/archived-plans/{date}-{plan_id}/metrics.md` (post-archive resolved path) |

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. This MUST happen before `default:archive-plan` runs, because archive moves `status.json` out of `.plan/plans/{plan_id}/` and `mark-step-done` would no longer find the plan.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step record-metrics --outcome done
```
