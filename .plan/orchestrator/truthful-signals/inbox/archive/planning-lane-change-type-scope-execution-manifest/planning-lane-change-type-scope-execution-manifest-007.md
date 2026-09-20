envelope_version=1
sender_type=plan
sender_id=planning-lane-change-type-scope-execution-manifest
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T16:01:50Z

# Dispatch-audit confidence is low at 0.058 channel completeness, so its clean 0/73 attests only self-consistency

component: plan-marshall:plan-retrospective
category: improvement
confidence: medium
source_plan: planning-lane-change-type-scope-execution-manifest
source_pr: 1399

## Context

The execution-context dispatch audit on this plan returned zero findings across all four categories. Read at face value that is a clean bill of dispatch discipline. Read with its own published populations it is not:

```
shape_violation:      evaluated_population 73, violations 0
dispatch_coverage:    19 steps -> 6 dispatched, 12 ran_inline, 1 no_evidence
channel_completeness: dispatch_line_count 7  (population: finalize_dispatcher_caller)
                      all_caller_dispatch_line_count 73
                      completion_count 121
                      ratio 0.058
                      confidence: low
```

The finalize dispatcher emitted **7** `[DISPATCH]` lines against **121** recorded step completions. And in `shape_violation.by_role`, every role's `foreign_caller_lines` equals its `dispatch_lines` exactly — `phase-6-finalize` 41/41, `verification-feedback` 18/18, and so on for all six roles.

## Root cause

The `shape_violation` check pairs the decision-log `effort resolve-target` records against the `[DISPATCH]` work-log lines. Both are written by the same seam, so a clean 0/73 shows the emitter's two writes agree — it does not show that dispatch discipline was verified. The audit's own standard says exactly this, and the `foreign_caller_lines` field exists to let a reader see it; on this plan that field equals `dispatch_lines` for every role, meaning the corroboration limit is at its maximum.

`ran_inline: 12` compounds it. That value means *a recorded zero token attribution* — an inline step **or** a dispatched step whose `<usage>` tag was not captured — so it is an upper bound on inline execution and never proof of it. With 68 of 68 dispatch-boundary rows carrying unmeasured token decomposition (see the sibling `manage-metrics` candidate), the evidence base for that classification is thin.

The audit did the right thing: it downgraded itself to `confidence: low` and published every denominator. The risk is entirely on the reading side — a zero-findings dispatch audit is the single most quotable line in the report, and the caveat that makes it meaningless sits three blocks away.

## Proposed action

Two small changes, both on the reporting side rather than the detection side:

1. When `channel_completeness.confidence` is `low`, have the fragment's `summary` line and its `counts.total: 0` carry the qualification inline rather than only in the `channel_completeness` block — the same "publish the population beside the count" discipline the script already applies per-block, applied to its own headline.
2. Investigate why the finalize dispatcher emits 7 lines for 121 completions. The `[DISPATCH]` emission is documented as automatic on the `effort resolve-target` seam, so either most finalize steps route around that seam or the seam is not firing; the audit reports `missing_dispatch_emission: 0`, which means the token-record cross-check found no step token-proven to have dispatched without a line — so the gap is more likely in which steps go through `resolve-target` at all.

## Evidence

- aspect: execution_context_dispatch_audit — `ratio: 0.058`, `confidence: low`, `by_role[].foreign_caller_lines == dispatch_lines` for all six roles
- aspect: logging_gap_analysis — recorded as `DISPATCH_CHANNEL_COMPLETENESS`, expected 121 / observed 7
- aspect: log_analysis — `top_tags` shows 73 `DISPATCH` lines total across every caller
