envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:46:09Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=medium
source_plan=plan-truth-148
source_aspects=execution_context_dispatch_audit,logging_gap_analysis

# Publish a token record per terminal finalize step - 13 of 16 have none

## Context

The dispatch audit classified the 16 terminal finalize steps of plan-truth-148 by their token record:
3 `dispatched`, 0 `ran_inline`, 13 `no_evidence`. The 13 without evidence are `architecture-refresh`,
`automatic-review`, `branch-cleanup`, `ci-verify`, `create-pr`, `finalize-step-simplify`,
`finalize-step-sync-baseline`, `pre-push-quality-gate`, `project:finalize-step-deploy-target`,
`project:finalize-step-era-stamp-fill`, `project:finalize-step-review-retrospective`,
`project:finalize-step-sync-plugin-cache`, and `push`.

The channel is correspondingly sparse: 11 finalize-scoped `[DISPATCH]` lines against 54 completions,
ratio 0.204, and the audit downgrades its own `confidence` to `low` on that basis rather than grading
a log-less phase `nominal`.

## Root cause

Token attribution reaches the status record only for steps that go through a dispatch boundary the
recorder observes. A step that runs without one leaves a zero, and a zero is what `ran_inline` counts
— so `ran_inline: 0` here means "no step recorded a zero", not "no step ran inline". The field is an
upper bound on inline execution and never proof of it.

## Proposed action

Do not paper over this with a default. The fix is to make each terminal step's execution mode
observable, not to guess it:

1. Emit a token record (even an explicit `unmeasured`) per terminal step, so `no_evidence` shrinks to
   the steps that genuinely cannot be measured.
2. Keep the three-state classification. Collapsing `no_evidence` into `ran_inline` would convert
   81% of the phase from "not measured" into a false claim about how it ran.
3. Raise the dispatch-line ratio by fixing emission at the seam rather than by hand-writing
   `[DISPATCH]` lines — a hand-written line cancels a missing seam emission and leaves the shape
   check green over a broken emitter.

## Evidence

- aspect: execution_context_dispatch_audit — `dispatch_coverage`: `evaluated_population: 16`,
  `dispatched: 3`, `ran_inline: 0`, `no_evidence: 13`, `missing_dispatch_emission: 0`
- aspect: execution_context_dispatch_audit — `channel_completeness`: `dispatch_line_count: 11`,
  `completion_count: 54`, `ratio: 0.204`, `confidence: low`
- aspect: logging_gap_analysis — the same 13-of-16 gap recorded as a phase-6-finalize STATUS gap
