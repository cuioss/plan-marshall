envelope_version=1
sender_type=plan
sender_id=plan-04-autonomy-gate-defaults
epic=operator-ux
kind=candidate-lesson
created=2026-09-07T12:46:12Z

# The dispatch context-load measure is dark for every plan: four optional flags that no call site passes

component: plan-marshall:manage-metrics
category: bug
confidence: high
source_signal: logging_gap_analysis gap DISPATCH_CONTEXT_LOAD; context_position_cost 0/23 measured
dedupe_note: Not covered by any filed candidate. The retrospective reported it as a gap in its own logging analysis and did not promote it to a lesson, so it would be lost when the plan directory is archived.

## The defect

`manage-metrics record-dispatch-boundary` declares four context-load columns — `--input-tokens`, `--output-tokens`, `--cache-read-input-tokens`, `--cache-creation-input-tokens`. All four are optional, each documented as *"Omit when unmeasured — the column is written as 'unmeasured', NOT as 0."*

Every one of this plan's **23** dispatch-boundary rows carries `unmeasured` in all four columns. The retrospective states the reach plainly: *"The four record-dispatch-boundary context-load flags are declared optional and are passed by no call site, so the whole measure is dark for every plan, not just this one."*

The consequence is that `position_multiple` — the per-dispatch context-position cost the measure exists to compute — reports `unmeasured` plan-wide, with `position_multiple_basis: unmeasured`. A metric with no producer.

## Why it matters on this epic in particular

This plan's own efficiency analysis raised four budget warnings, one of them *"one phase owns 55 percent of dispatched tokens — 6-finalize outspent 5-execute 2.8 to 1"*, driven by finalize re-fires (`pre-push-quality-gate` 6x, `automatic-review` 5x, `plugin-doctor` 4x). Per-dispatch context-load is exactly the measure that would say whether a re-fire is expensive because of the work it does or because of the context it reloads. The question the budget warnings raise is the question this dark measure was built to answer.

## Corrective

Two admissible fixes, and the choice is a real one:

1. **Feed it.** Have the dispatcher call sites pass `message.usage` on every `record-dispatch-boundary` invocation, so the columns carry values and `position_multiple` becomes derivable.
2. **Retire it.** If no call site can supply `message.usage`, the four flags and the `context_position_cost` aspect that consumes them are dead surface, and keeping them makes every retrospective report a measurement gap that is really an absent producer.

What is not admissible is the present state: a declared measure, a report field that faithfully says `unmeasured` on every row of every plan, and no producer anywhere. The honest reporting is working correctly and is the only reason the gap is visible at all — that part should be preserved under either fix.
