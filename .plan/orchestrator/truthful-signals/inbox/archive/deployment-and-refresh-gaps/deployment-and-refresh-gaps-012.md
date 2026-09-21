envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:45Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `refresh-path-gate-and-invariant-gaps` (PR #687), original message `refresh-path-gate-and-invariant-gaps-001.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

# Candidate lesson: a completeness discriminator must be DERIVED from the observation, not asserted beside it

## Shape

Two independent surfaces in this run reported a verified fact they had never
verified. Both were structurally the same defect, so they are one rule:

> When a payload carries both a **count/verdict** and a **discriminator that
> vouches for it** (`*_population: measured`, `participation_complete: true`,
> `store_resolution: present`), the discriminator MUST be computed from the
> same read that produced the count. A discriminator assembled from a
> different, cheaper source — a return code, the presence of a response body,
> a step's own success — is not evidence; it is a second claim that happens to
> sit next to the first.

## Site 1 — build wrapper: `tests_run: 0` with `tests_population: measured`

The build wrapper returned:

- `tests_run: 0`
- `tests_population: measured`

while the underlying Maven log carried **465 test-result lines**. `measured`
is precisely the token that tells a caller "this zero is real, tests genuinely
did not run" as opposed to "I could not read the count". A caller trusting the
TOON — which is what the discriminator exists to make safe — concludes no tests
ran and that the build proved nothing, when in fact a full suite passed.

The failure is that `tests_population` was set from the wrapper's own
belief that it had parsed, not from the parse actually yielding rows. The
correct derivation: `measured` iff the parser matched >= 1 test-result line;
otherwise `unparsed`, and a zero under `unparsed` is a could-not-read zero.

## Site 2 — review-bot rate-limit refusal classified as participation

A review bot replied with a rate-limit refusal — in substance *"you have used
your own review budget"*. The completion classifier saw a non-empty
`review_body` and recorded the bot as **participated**; the completeness guard
then reported `participation_complete: true`.

Nothing was reviewed. A refusal is a response, and the classifier was keyed on
*a response existing* rather than on *a review having been performed*. This run
was non-blocking only by luck: that particular bot was optional. Had it been a
required bot, the merge gate would have passed on a review that never happened.

Filed in-run as finding `a4d043`.

The correct derivation: a bot's completion state must be decided on review
CONTENT class (findings emitted / explicit clean verdict) with refusal,
rate-limit, and error bodies forming their own `refused` state that is NOT
`participated` and does NOT satisfy the completeness guard.

## Why this is reusable

The plan-marshall corpus already encodes this rule for stores — the "every
zero states which kind of zero it is" discipline in `manage-lessons
list-stalled`, `manage-findings findings_store_state`, and `inbox list`'s
three-zero table. Both sites above are the SAME rule applied to two surfaces
that were never brought under it:

- a **build wrapper**, whose zero-test count needs a parse-derived population;
- a **review-participation guard**, whose completeness needs a content-derived
  participation state.

The generalizable check when auditing any such surface: ask *what read would
have to fail for this discriminator to be wrong, and does the code branch on
that read?* If the discriminator cannot be falsified by the same failure that
falsifies the count, it is decorative.

## Suggested disposition

Both sites are worth fixing. Site 1 is a defect in the build wrapper's
TOON contract; Site 2 is a defect in review-bot completion classification and
is the higher-severity of the two because it sits on the merge path.
