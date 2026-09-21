envelope_version=1
sender_type=plan
sender_id=wait-for-comments-counts-rows
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T17:46:02Z

# record-dispatch-boundary call sites never forward the four-field usage view

component: plan-marshall:manage-metrics
category: bug
confidence: medium
source_plan: wait-for-comments-counts-rows
source_pr: 1071

## Context

`record-dispatch-boundary` accepts four per-dispatch context-load columns — `--input-tokens`,
`--output-tokens`, `--cache-read-input-tokens`, `--cache-creation-input-tokens` — documented as the
per-DISPATCH counterpart to the per-PHASE four-field view that `enrich` writes.

Across all 13 dispatch-boundary rows this plan recorded (1 in `4-plan`, 2 in `5-execute`, 10 in
`6-finalize`), **every one of those four columns is `0`**:

```
"2026-08-01T13:09:42Z",task_batch_complete,176479,69,580732,0,0,0,0
"2026-08-01T14:51:57Z",voluntary_checkpoint,439389,226,5723054,0,0,0,0
"2026-08-01T16:18:59Z",step_complete,382431,83,875045,0,0,0,0
...
```

The legacy five columns (`total_tokens`, `tool_uses`, `duration_ms`, plus timestamp and cause) are
populated correctly on every row. Only the four appended columns are dead.

Because they default to 0 rather than being absent, the emptiness is invisible to any consumer that
reads the columns rather than auditing them: a per-dispatch billing-cost analysis over this plan
would silently report zero cache reads and zero cache creation for every dispatch.

## Root cause

The columns were added to the script's argument surface, but no call site was updated to forward the
dispatched agent's four-field `message.usage` view at termination. The defaults-to-0 design means the
gap produces plausible-looking data instead of an error — the same shape as a producer whose output
is never checked.

## Proposed action

- Update every `record-dispatch-boundary` call site (the `plan-marshall` orchestrator's phase-Task
  return handlers) to forward the four fields from the returning agent's usage envelope.
- Consider making the four columns emit an explicit sentinel (empty, not `0`) when not supplied, so a
  non-forwarding call site is distinguishable from a dispatch that genuinely consumed no cache.
- Add a retrospective assertion: if every row in a plan's dispatch-boundary file carries four zeros,
  report it as a measurement gap rather than as a measurement.

## Evidence

- aspect: execution-context-dispatch-audit — `context_load_attribution` all four fields `0` across 13 rows in 3 phases.
- `work/metrics-dispatch-boundaries-4-plan.toon`, `-5-execute.toon`, `-6-finalize.toon` — full row dumps in the compiled `quality-verification-report.md` Log Analysis section.
