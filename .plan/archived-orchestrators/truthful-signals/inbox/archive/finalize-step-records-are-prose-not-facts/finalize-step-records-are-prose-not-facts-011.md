envelope_version=1
sender_type=plan
sender_id=finalize-step-records-are-prose-not-facts
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T12:18:28Z

component=plan-marshall:manage-metrics
category=bug
confidence=high
source_plan=finalize-step-records-are-prose-not-facts
source_pr=1076
source_aspects=log_analysis,logging_gap_analysis

# record-dispatch-boundary accepts termination causes SKILL.md does not document

## Context

`manage-metrics/SKILL.md` documents `--termination-cause` as a closed set and states it explicitly: "Required — missing or unrecognised values are rejected as script errors (there is no implicit fallback)". The documented values are:

```
voluntary_checkpoint | task_complete_returned_verbatim | budget_yield |
harness_cancellation | error | clean_exit_queue_empty
```

This plan's dispatch-boundary artifacts contain 16 rows:

- `work/metrics-dispatch-boundaries-4-plan.toon` — 1 row, `task_batch_complete`
- `work/metrics-dispatch-boundaries-5-execute.toon` — 5 rows: 2 `harness_cancellation`, 3 `voluntary_checkpoint`
- `work/metrics-dispatch-boundaries-6-finalize.toon` — 10 rows, all `step_complete`

11 of 16 rows (69%) carry a value that is not in the documented enum. The recorder accepted every one of them.

## Root cause

The producer side (the `phase-4-plan` and `phase-6-finalize` call sites) emits vocabulary the consumer-facing contract does not declare. Either the argparse `choices` list was widened without the SKILL.md enum following, or the enum was never a `choices` constraint at all and the "rejected as script errors" sentence is aspirational.

The downstream cost is concrete, not cosmetic. `logging-gap-analysis`'s `DISPATCH_TERMINATION_CAUSE` rule is specified to report "the per-cause distribution over the canonical value set" and to fire a warning when `voluntary_checkpoint + task_complete_returned_verbatim` exceed 50% of recorded dispatches. With 69% of rows outside the canonical set, both the distribution and the denominator are undefined — the rule cannot say whether it is looking at agent-initiated re-dispatch or at ordinary step completion.

## Proposed action

1. Decide which of the two vocabularies is canonical. `step_complete` and `task_batch_complete` are semantically useful (they distinguish a finalize step's normal exit and a plan-phase batch exit from an agent-initiated checkpoint), so widening the enum is likely the right call — not narrowing the producers.
2. Whichever way it resolves, make the argparse `choices` and the SKILL.md enum the same list, derived from one source, and add a population-derived test that asserts every value any call site emits is in the declared set.
3. Update `logging-gap-analysis.md`'s `DISPATCH_TERMINATION_CAUSE` rule to state the denominator explicitly, and to exclude the normal-exit causes from the >50% agent-initiated threshold the same way `budget_yield` is already excluded.

## Evidence

- aspect: log_analysis — `dispatch_boundaries` block: `4-plan` 1 row `task_batch_complete`; `6-finalize` 10 rows `step_complete`
- `manage-metrics/SKILL.md` § `record-dispatch-boundary` — the six documented values and the "no implicit fallback" sentence
- `plan-retrospective/references/logging-gap-analysis.md` § DISPATCH_TERMINATION_CAUSE — "the per-cause distribution over the canonical value set"
