envelope_version=1
sender_type=plan
sender_id=plugin-doctor-detector-coverage-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T07:36:56Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
created=2026-08-25

# Derive every set/count/partition claim in self-review prose, never read it off what was in view

## Context

During this finalize's settle band (17 rounds, 6 firings 3 rounds in a row failed), the same mistake
recurred 5 times across 3 consecutive rounds inside the self-review dispatcher's own replacement prose:
a "Called by" table naming 1 caller of several, a "seven of ten bullets checked" count that
double-booked one bullet and dropped two others so the arithmetic still summed to ten, an "exactly
seven subcommands" claim contradicted by a table nine lines below it, an "appears only in an error
message" claim refuted by a comment occurrence, and a "produces no diagnostic anywhere" claim refuted
by a warning elsewhere in the tree.

## Root cause

Each instance asserted completeness (a set, a count, or a partition) as a rhetorical summary of what
the author had looked at, rather than deriving it from an independent enumeration of the population.
The errors were individually plausible and in one case (the bullet count) two mistakes cancelled each
other's arithmetic, which is exactly why it survived two rounds unnoticed.

## Proposed action

Add this as an explicit self-review interpretation rule: before writing a set, a count, a partition,
an exhaustive-search claim, or a nothing/only/anywhere universal into documentation, the author must
derive it from an independent enumeration of the population. If it cannot be derived, write examples
and explicitly disclaim exhaustiveness -- and note that the disclaimer does not license a false
example; every example given must still be individually true.

## Evidence

- aspect: script_failure_analysis -- 5 contract_drift/touched_claim_unverified findings in one
  defect_class across rounds 3-5 of this plan's settle band (finding 4e23cf)
- aspect: plan_efficiency -- settle-band findings-per-round series (1/8/7/4/6/9/4/1/1/1/0/2/4/3/11/1/0)
  shows the recurrence clustering inside the mid-band rounds this lesson covers
