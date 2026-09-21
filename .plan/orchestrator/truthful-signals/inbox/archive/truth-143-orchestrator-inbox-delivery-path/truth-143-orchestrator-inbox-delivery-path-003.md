envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:18:13Z

# Finalize dispatch boundaries record zero tokens for the last 41 of 77 rows

component: plan-marshall:manage-metrics
category: bug
confidence: high

## Context

`work/metrics-dispatch-boundaries-6-finalize.toon` holds 77 rows for this plan. The first 36 carry plausible measurements (token totals from 55,057 to 479,509, tool-use counts from 3 to 66, durations from 26s to 16m). Every one of the last 41 — contiguously, from `2026-09-19T15:23:40Z` to the end of the phase — carries `total_tokens: 0`, `tool_uses: 0`, `duration_ms: 0`, while still recording a valid `termination_cause` of `step_complete`.

These are not idle rows. The steps recorded in that window include `project:finalize-step-deploy-target` (1208 files emitted), `project:finalize-step-sync-plugin-cache` (10 bundles synced, executor regenerated, daemon upgraded) and `project:finalize-step-review-retrospective` (3 reviewers compared) — all substantial dispatched work recording zero spend.

The plan's `script-execution.log` records three argparse rejections of `plan-marshall:manage-metrics:manage-metrics accumulate-agent-usage` (exit 2), the first at `2026-09-19T15:23:28Z` — twelve seconds before the first zeroed row.

## Root cause

Not proven. The temporal coincidence is tight (12 seconds) and the zeroing is contiguous to the end of the phase rather than intermittent, which is the shape of a recording path that stopped working rather than of individual dispatches that genuinely spent nothing. The most likely reading is that `accumulate-agent-usage` was the write path for the token attribution, its invocation shape was rejected, and the fallback wrote a structural zero instead of recording that it could not measure.

The consequence is independent of the cause, and is the part that matters here. `metrics.md` renders `6-finalize` as `7,176,034` tokens with the note that `dispatch_boundary_total` **won the reconciliation maximum** against `total_tokens` (4,757,132). So the figure the report presents as the phase total — and which feeds the plan total of 14,414,932 — is a floor computed over 36 measured rows, presented as a total over 77, and it won the reconciliation precisely because it was the larger number.

## Proposed action

1. Make the recorder distinguish *"this dispatch spent nothing"* from *"this dispatch's spend was not captured"*. A row whose token attribution could not be read must record an unmeasured sentinel, not `0` — the same discipline `inline_main_context_tokens: unmeasured` already uses one block away in the same store.
2. Have the dispatch-boundary reader publish `rows_measured` / `rows_unmeasured` beside `dispatch_boundary_total`, and mark the total a FLOOR whenever `rows_unmeasured > 0`. The reconciliation note that picks the largest eligible measure must then treat a floor as ineligible to win outright, or must label the winner as a floor.
3. Fix the `accumulate-agent-usage` invocation shape (three rejections logged) and add a non-zero-exit alarm on that call site rather than letting it degrade silently.

## Evidence

- artifact: `work/metrics-dispatch-boundaries-6-finalize.toon` — rows 37 through 77, all `0,0,0`, contiguous from `2026-09-19T15:23:40Z`
- aspect: script_failure_analysis — `plan-marshall:manage-metrics:manage-metrics accumulate-agent-usage`, exit 2, first at `2026-09-19T15:23:28Z`, occurrence_count 3
- artifact: `metrics.md` — "6-finalize -> dispatch_boundary_total 7,176,034 (> total_tokens 4,757,132)" recorded as the reconciliation winner
- aspect: plan_efficiency — that figure is the `dominant_phase` and 49.8% of the reported plan total
