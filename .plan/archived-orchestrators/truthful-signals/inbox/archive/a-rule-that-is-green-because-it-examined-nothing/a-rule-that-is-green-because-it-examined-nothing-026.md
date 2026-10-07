envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T19:01:11Z

component=plan-marshall:phase-6-finalize
category=insight
title=Owed architecture hint: review findings are tolerated as a deliberate tradeoff

## Owed `architecture enrich` call

- **Target module**: `default` (cross-cutting — the recurrence carries no concrete module attribution)
- **Enrich verb**: `insight`
- **Generalized hint text** (verbatim):

  > The project tolerates review-bot findings as a deliberate tradeoff: bot
  > meta-comments and review summaries are routinely accepted rather than acted
  > on, because they request no change to the diff under review.

## Reconstruction context

Within-plan recurrence: `(default, pr-comment, accepted)` × 4, against a
`preference_min_recurrence` threshold of 2.

## Caveat the orchestrator should weigh before promoting this

This is the **coarsest possible generalization**. The module collapsed to
`default` because `pr-comment` findings carry no module attribution, and the
finding-class collapsed to the bare finding *type*, so the tuple is effectively
"review comments, accepted" rather than a pattern about any particular code
area. All four contributing findings are bot meta-comments or review summaries
— exactly the class a producer pre-filter is supposed to drop before triage.
The recurrence may therefore be evidence of a **pre-filter gap** rather than of
a durable project preference. Promoting it as an architecture hint would bias
future outlines on a signal that says little about the codebase.
