envelope_version=1
sender_type=plan
sender_id=lesson-retirement-fails-open
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:02:50Z

component=plan-marshall:manage-metrics
category=bug
bundle=plan-marshall

# Two phase-6 token ledgers disagree and neither one is complete

## Context

Phase 6-finalize of plan `lesson-retirement-fails-open` is recorded twice, by two
independent ledgers that disagree:

| Ledger | Rows | Tokens |
|--------|-----:|-------:|
| `execution.toon` → `execution_log` (6-finalize, token-bearing) | 9 | 1,386,494 |
| `work/metrics-dispatch-boundaries-6-finalize.toon` | 11 | 2,108,919 |
| union of both | 12 | 2,163,290 |

Neither is a superset of the other. The boundary ledger holds three dispatches the
`execution_log` never recorded (224,975 + 228,496 + 323,325 = 776,796 tokens, the
self-review repair rounds). The `execution_log` holds one dispatch the boundary
ledger never recorded (`project:finalize-step-plugin-doctor` round 2, 54,371).

The union is itself a floor, not a total. Three finalize steps completed after
17:35Z — `project:finalize-step-deploy-target`,
`project:finalize-step-sync-plugin-cache` and
`project:finalize-step-review-retrospective` — and appear in NEITHER ledger; the
last of those is a dispatched LLM step that demonstrably ran an envelope. The
retrospective's own envelope is uncounted as well.

Meanwhile `metrics.md` publishes a plan Total of 2,276,592 correctly labelled
`(n=4/6)`. That labelling is the truthful-signals fix working as intended — the
Total names its population. But the phase whose spend exceeds the entire labelled
Total is the one phase the label says is missing.

## Root cause

Two recorders write the same fact through different call sites with different
trigger conditions — `manage-execution-manifest record-step` fires on step
completion, `manage-metrics record-dispatch-boundary` fires on envelope
termination — and no consumer reconciles them or asserts that either covers the
phase. A step that completes without a boundary record, or a boundary that
terminates without a step record, is silently absent from whichever ledger a
reader happens to consult.

## Proposed action

Add a `manage-metrics` verb that unions the two ledgers for a phase, reports the
rows present in one and absent from the other, and refuses to publish a phase total
without naming the union coverage — the same discipline `metrics.md`'s `(n=4/6)`
Total already applies at plan granularity, applied one level down. Any consumer
reading a per-phase figure should read it from that verb, never from one ledger.

## Impact

Phase-6 is the most expensive phase in this run by a wide margin and the only one
with no published token figure. Any cost analysis, budget anchor calibration, or
lane-lever measurement that reads `execution.toon` alone sees 64 percent of the
measured spend and 0 percent of the label that would say so.

## Evidence

- aspect: plan_efficiency — `measured_phase_6_floor.dispatched_leaf_tokens: 2163290`, `dispatches_known_missing: 3`
- aspect: log_analysis — `dispatch_boundaries.6-finalize` 11 rows, `unknown_count: 0`
- aspect: routing-decisions — `cost_preview.actual_tokens: 1386494`, sourced from `execution_log` alone
- artifact: `metrics.md` — "Partial: unrecorded phases — 6-finalize", Total `2,276,592 (n=4/6)`
