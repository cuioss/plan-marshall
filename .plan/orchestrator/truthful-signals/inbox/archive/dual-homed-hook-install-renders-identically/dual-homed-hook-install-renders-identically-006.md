envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T09:50:10Z

component=plan-marshall:phase-2-refine
category=improvement
confidence=medium
source_plan=dual-homed-hook-install-renders-identically
source_aspects=request_result_alignment,chat_history_analysis

# Premise verification must publish the claim set it checked beside its verdict

## Context

`phase-2-refine` logged, at 2026-09-02T15:18:01Z:

```
[REFINE:3] Source premise verification: 4 claims checked, 4 valid, 0 invalid
```

Twenty minutes later, `phase-3-outline` logged:

```
Root-cause check refuted half the request premise: the hook check already
discriminates the dual-homed case in prose at _claude_runtime_impl.py:2100 and
an existing test pins it; only the display check renders identically.
```

Both statements are true. The refine line is true of the four claims it took; the outline line is true of the request. But `4 valid, 0 invalid` reads as a verdict on the premise, and the premise was half wrong. Nothing in the refine record says which four claims were checked, so a reader cannot tell whether the refuted claim was examined and passed or was never in the population.

This is the epic's own archetype committed by a gate: a confident count over an unpublished population.

## Root cause

The verification publishes its result (`4 valid`) and its size (`4 claims`) but not its membership, and it does not state what fraction of the request's assertions the four represent. A check that examines a subset and reports a clean total over that subset is indistinguishable, from the log alone, from one that examined everything.

## Proposed action

Emit the claim set, not just its cardinality: one line per checked claim with its verdict, plus an explicit statement of what was NOT checked (or a derivation of the request-assertion population the four were drawn from). Where the population cannot be enumerated, say so — an unenumerable population makes `4 valid, 0 invalid` a floor, not a verdict.

## Evidence

- work.log 2026-09-02T15:18:01Z — `[REFINE:3] ... 4 claims checked, 4 valid, 0 invalid`
- decision.log 2026-09-02T15:38:43Z — `Root-cause check refuted half the request premise`
- aspect: request_result_alignment — `premise_verification.gap_minutes: 20`
- Outcome note: the refutation was caught before any code was written and correctly narrowed the plan. The machinery worked; this lesson is about the earlier gate's wording, not the outcome.
