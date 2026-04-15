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

## Display Plan Completion Summary

Display the plan completion summary including core metrics:

```
## Plan Complete: {plan_id}

| Metric | Value |
|--------|-------|
| Total Duration | {formatted total_duration from metrics} |
| Total Tokens | {total_tokens from metrics} |
| PR | #{pr_number from earlier create-pr step, or "n/a"} |
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
