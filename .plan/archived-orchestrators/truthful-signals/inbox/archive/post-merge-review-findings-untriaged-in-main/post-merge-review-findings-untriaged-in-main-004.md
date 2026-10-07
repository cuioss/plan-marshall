envelope_version=1
sender_type=plan
sender_id=post-merge-review-findings-untriaged-in-main
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:44:32Z

component=plan-marshall:phase-3-outline
category=anti-pattern
created=2026-07-29
bundle=plan-marshall

# A deliverable's declared selection rule under-scoped against its own stated OBJECTIVE

The declared D1 selection rule (post-merge-landed OR unresolved-thread) under-selected against the
spec's own OBJECTIVE section, which called for gathering every post-merge review finding across the
derived population. Widening the rule to match the objective added 7 more findings AND exposed that
PR #1032 satisfied the ORIGINAL, narrower rule and had still been missed outright by the first pass.

## Solution

When authoring a deliverable's selection/derivation rule, cross-check it against the spec's own
OBJECTIVE prose before treating the rule as settled — a rule that reads as a faithful restatement of
the objective can still silently narrow it. Re-derive the population once against the widened rule
and diff the two result sets before accepting the narrower one as complete.

## Impact

This is the epic's most-recurring failure shape restated one level up: not just "a named list is a
sample, not the population" (confirmed 4+ times already), but "a *rule* can encode the same
under-coverage as a named list" — a rule that looks like a faithful restatement of an objective is
not automatically equivalent to it, and the gap can hide a member the narrower rule should have
caught even under its own terms.
