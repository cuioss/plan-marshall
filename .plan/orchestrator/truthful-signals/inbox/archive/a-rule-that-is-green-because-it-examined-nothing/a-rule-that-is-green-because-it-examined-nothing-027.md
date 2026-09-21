envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T19:01:41Z

component=plan-marshall:phase-6-finalize
category=insight
title=Owed architecture hint: out-of-scope review suggestions are a standing consideration

## Owed `architecture enrich` call

- **Target module**: `default` (cross-cutting — the recurrence carries no concrete module attribution)
- **Enrich verb**: `insight`
- **Generalized hint text** (verbatim):

  > The project treats review suggestions that reach beyond the diff under
  > review as a standing consideration rather than a defect: they are recorded
  > with rationale and deferred to a dedicated plan, not folded into the PR that
  > surfaced them.

## Reconstruction context

Within-plan recurrence: `(default, pr-comment, taken_into_account)` × 3, against
a `preference_min_recurrence` threshold of 2.

## Caveat the orchestrator should weigh before promoting this

Same coarseness caveat as the sibling message: the module collapsed to `default`
and the finding-class collapsed to the bare finding *type*, so the tuple carries
no information about any particular code area.

This one is nonetheless the **stronger** of the two. Its three contributing
dispositions share a real, articulable rationale — each declined a suggestion
that targeted files the PR did not modify (Scope Out of Bounds), and each said
so explicitly in its resolution detail. That is a genuine standing convention
about scope discipline, not a pre-filter artifact. The generalization above is
worth keeping even if the sibling is dropped.
