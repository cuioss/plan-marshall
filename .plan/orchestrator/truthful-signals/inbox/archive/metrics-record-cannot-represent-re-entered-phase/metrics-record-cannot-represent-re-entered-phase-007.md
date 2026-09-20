envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T21:03:25Z

# Candidate lesson: publishing an empty population instead of manufacturing a verdict — and refusing the back-fill that would have made the check tautological

**Source**: Q-Gate finding `85e540` (3-outline), resolved `accepted`
**Defect class**: vacuous-authority / unearned verdict (handled WELL — this is an exemplar, not a defect report)
**Theme fit**: confident-signal-hides-a-caveat — the confident signal here is a zero

## What happened

The 3-outline assessment-coverage check (§2.2) and the Step 5 missing-coverage check both ran
against an **empty population**. `manage-findings assessment list --certainty CERTAIN_INCLUDE`
returned `total_count: 0`, `filtered_count: 0`. Neither check was evaluable against any of the
declared affected-file paths across the outline's 4 deliverables.

Two readings were available and **both were dishonest**:

- A literal reading of the §2.2 rule over an empty assessed set flags all declared paths as
  missing an assessment — a manufactured failure.
- Reporting the two checks as clean manufactures a verdict from an absent population — *the exact
  defect shape this plan exists to fix.*

So the population size was **published** instead, and the checks were declared NOT EVALUATED with
the consequence named: their silence must not be read as coverage.

## The part worth preserving — why the back-fill was refused

The obvious remedy was to back-fill: write one `CERTAIN_INCLUDE` row per path already listed in
Affected files, giving §2.2 a real population. That was **rejected on substance, not on cost**:

> Writing one row per already-listed path would make §2.2 **tautological**, because the writer and
> the checked-against set would be the same agent in the same phase — so the check could never
> fail and would certify nothing. Installing that vacuous guard while resolving a finding about
> unearned verdicts would reproduce this plan's own defect archetype.

And the closing line, which is the whole lesson in one sentence:

> **A manufactured population is worse than an absent one, because an absent one is visible.**

The resolution also named the **residual risk carried rather than closed**: with no store, the
outline has no independent guard against a deliverable listing a file discovery never examined,
beyond the published consumer-sweep queries.

Note also the diagnostic tell that was recorded rather than swallowed: the plan was deep-lane, and
deep lane is where discovery normally writes `CERTAIN_INCLUDE` assessments — so the empty store is
itself a signal that the domain component-analysis dispatch did not run.

## Candidate rule

> A check that returns 0 over an empty population has not passed; it has not run. Publish the
> population size alongside every set-based verdict, and mark the check NOT EVALUATED rather than
> clean.

> Never back-fill a population from the same set the check will be evaluated against. If the
> writer and the checked-against set are the same agent in the same phase, the check is
> tautological and certifies nothing — prefer the visible gap.

> Resolution disposition matters: this was resolved `accepted` rather than `taken_into_account`
> **because the gap is declared and published, not closed**. That distinction is worth enforcing
> generally — `taken_into_account` should not be used for a gap that remains open.
