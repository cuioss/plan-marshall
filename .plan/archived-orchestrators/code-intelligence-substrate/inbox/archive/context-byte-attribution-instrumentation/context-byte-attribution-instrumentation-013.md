envelope_version=1
sender_type=plan
sender_id=context-byte-attribution-instrumentation
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-03T16:56:56Z

category=improvement
component=plan-marshall
source=finalize-step-preference-emitter
plan_id=context-byte-attribution-instrumentation
owed_enrich_module=plan-marshall
owed_enrich_verb=best-practice
title=Aggregation figures over an unconstrained population recur as a review-caught defect shape in plan-marshall

## Owed architecture enrich

- `--module`: `plan-marshall`
- verb: `architecture enrich best-practice --module plan-marshall`
- hint text (verbatim, to be passed as the enrichment body):

> When a figure aggregates over a parsed or discovered population, constrain the
> population at the point of accumulation rather than at the point of reporting.
> Two independent review findings in this module landed on the same shape: a
> parser admitted every bracketed section as a phase so a non-phase roll-up
> inflated the corpus denominator, and a summary metric added two independent
> per-plan tallies so a plan tripping both was counted twice. In both cases the
> predicate was stated precisely while the set it ranged over was left implicit.
> Name the set the figure is over, and derive it from the authoritative
> definition rather than from whatever the parser happened to yield.

## Why this cleared the threshold

Within-plan recurrence of `(module=plan-marshall, finding-class=pr-comment,
disposition=fixed)` = 2, against `preference_min_recurrence` = 2.

Both instances resolve to module `plan-marshall` via `architecture which-module`
on `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`.

The dispositions are generalized here, not logged raw, per the
disposition-to-hint privacy invariant.

## Note for pickup

This overlaps the `-011` population-scoping candidate-lesson `lessons-capture`
routed on the same run, which reached the same shape from the review side. They
should very likely merge on pickup — this message is the preference-learning
arm's independent arrival at it, and the agreement between two different
detectors is itself the signal.
