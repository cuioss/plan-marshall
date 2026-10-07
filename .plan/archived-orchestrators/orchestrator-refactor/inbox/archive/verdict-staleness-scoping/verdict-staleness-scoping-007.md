envelope_version=1
sender_type=plan
sender_id=verdict-staleness-scoping
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-22T21:28:42Z

# Finalize dispatch channel sparse: 9 of 16 steps carry no token evidence

## Metadata

- component: `plan-marshall:phase-6-finalize`
- category: improvement
- confidence: medium
- observed_in_plan: verdict-staleness-scoping

## Context

`check-dispatch-audit` classified the 16 terminal finalize steps by token record: 5
`dispatched`, 2 `ran_inline`, 9 `no_evidence`. `channel_completeness` graded its own
`confidence: low` at `ratio: 0.273` (9 finalize-scoped dispatch lines against 33 completions).
The nine steps with no evidence include `push`, `create-pr`, `ci-verify`, `automatic-review`,
`branch-cleanup`, `architecture-refresh` and three project-local steps.

## Root cause

Two independent evidence sources are meant to corroborate each other — the `[DISPATCH]`
work-log line and the per-step token record — and on this plan neither is populated for more
than half the steps. The audit reports this honestly rather than grading the plan `nominal`,
and it correctly marks `ran_inline_claim_strength: ceiling`. But the consequence is that the
audit's headline clean result (`shape_violation 0/35`) rests on a channel that saw a minority
of the population, and `corroboration: uncorroborated` says as much.

## Proposed action

Establish why 9 of 16 finalize steps produce no token attribution — whether they genuinely run
inline, or whether the `<usage>` capture is not wired on those step paths. Until that is known,
the dispatch audit cannot distinguish an inline step from an uninstrumented dispatched one, and
`ran_inline` stays an upper bound that no consumer should read as a measurement.

## Evidence

- aspect: execution_context_dispatch_audit — `dispatch_coverage`: 5 dispatched / 2 ran_inline / 9 no_evidence of 16
- aspect: execution_context_dispatch_audit — `channel_completeness`: `ratio: 0.273`, `confidence: low`, 9 finalize-scoped lines vs 35 all-caller lines
- aspect: execution_context_dispatch_audit — `shape_violation.corroboration: uncorroborated` over `foreign_caller_line_total: 35`
