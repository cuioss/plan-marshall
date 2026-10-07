envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:50:53Z

# Separate by-design-inline finalize steps from a lost token record

component: plan-marshall:phase-6-finalize
category: improvement
confidence: medium
source_plan: plan-truth-157
source_aspects: execution_context_dispatch_audit

## Context

The dispatch audit's `dispatch_coverage` block classified the 16 terminal finalize steps as 7 `dispatched`,
0 `ran_inline`, and 9 `no_evidence`, with `missing_dispatch_emission: 0`. `channel_completeness` graded its
own `confidence: low` at `ratio: 0.385` (10 finalize-scoped dispatch lines against 26 completions).

The nine `no_evidence` steps are the mechanical ones: `finalize-step-sync-baseline`,
`pre-push-quality-gate`, `push`, `architecture-refresh`, `ci-verify`,
`project:finalize-step-era-stamp-fill`, `branch-cleanup`, `project:finalize-step-deploy-target`, and
`project:finalize-step-sync-plugin-cache`. Several of those plausibly run inline by design and would never
produce a dispatch token record at all.

The audit cannot tell that apart. `no_evidence` means "no readable token record", which covers both an
expected absence (a step that never dispatches) and a real instrumentation gap (a step that dispatched and
whose record was lost). The block is honest about this — it publishes its population and downgrades its own
confidence rather than grading the plan clean — but the consequence is that a coverage ratio of 0.385 cannot
be acted on, because most of its shortfall may be entirely correct.

## Root cause

Coverage is computed over *all* terminal finalize steps, while only a subset of them dispatch. Nothing in
the step's own declaration says which subset, so the denominator includes steps that can never contribute to
the numerator, and the residual bucket conflates two states with opposite remedies.

## Proposed action

Let a finalize step declare whether it dispatches. Then:

- `no_evidence` splits into `declared_inline` (expected, not a gap) and `record_unreadable` (a real
  instrumentation gap worth a finding).
- The coverage ratio is computed over the dispatching population only, so a low ratio means something.
- `ran_inline` keeps its existing upper-bound semantics; this change removes the steps that were never
  candidates from the comparison rather than reinterpreting the ones that were.

## Evidence

- aspect: execution_context_dispatch_audit — `dispatch_coverage` reports
  `evaluated_population: 16, dispatched: 7, ran_inline: 0, no_evidence: 9`
- aspect: execution_context_dispatch_audit — `channel_completeness` reports `ratio: 0.385` with
  `confidence: low`, `dispatch_line_count: 10` over `dispatch_line_population: finalize_dispatcher_caller`
- The nine `no_evidence_steps` are named in the fragment and are, by inspection, the mechanical steps

## Confidence rationale

Recorded at medium, not high: from inside this envelope it cannot be established which of the nine steps
dispatch by design. That determination is exactly what the proposed declaration would make explicit, so
asserting a defect count here would pre-judge the thing the fix exists to reveal.
