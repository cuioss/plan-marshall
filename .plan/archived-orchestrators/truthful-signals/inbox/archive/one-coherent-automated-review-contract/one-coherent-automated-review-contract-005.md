envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T21:05:42Z

component=plan-marshall:automatic-review
category=improvement
bundle=plan-marshall

# A size-keyed bot refusal is unrecoverable by any wait-and-retry strategy — a big PR silently loses that reviewer

## Observation

On PR #1041 (PLAN-92) Sourcery hard-refused because the diff exceeded its 150 000-character
limit. Unlike a rate limit, this refusal is keyed on **diff size, not on time**: waiting changes
nothing, a new-commits event changes nothing, a trigger comment changes nothing. Every recovery
strategy in the D4 family is structurally inapplicable.

PLAN-92's per-bot registry already models this correctly — each bot declares
`awaitable-window` vs `hard-quota`, and Sourcery's refusal classifies as `refused-hard` in the
shipped failure taxonomy, so the contract did not pretend a retry was possible. The gap is not
in the classification; it is that no plan-side practice exists for the consequence.

## The consequence

Any plan whose PR exceeds the vendor limit loses that reviewer entirely, and there is no signal
at *planning* time that this will happen — it surfaces only at finalize, after the diff already
exists. On this PR the loss was tolerable because Sourcery is classified `optional`. Had it been
`required`, the plan would have hit an unrecoverable gate at the end of a long run.

## Do this instead

- Treat a `refused-hard` (size-keyed) outcome as a **terminal coverage gap on that PR**, recorded
  explicitly, never as a transient to retry. Never let a recovery loop spend attempts on it.
- Where a size-limited bot is classified `required`, the size ceiling becomes a de-facto planning
  constraint: either decompose the deliverable so the PR stays under the vendor limit, or
  reclassify the bot to `optional` deliberately rather than discovering the wall at finalize.
- Do not attempt to "work around" the limit by splitting the PR after the fact at merge time —
  the decision belongs at decomposition.

## Open question for the epic

Should a large-diff plan owe an explicit accepted-coverage-gap record when a size-limited bot
refuses, in the same way partial required-bot coverage owed an explicit operator decision on
this PR? This is a policy question above any single plan.
