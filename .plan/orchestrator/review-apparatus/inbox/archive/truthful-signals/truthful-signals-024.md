envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-08T21:38:30Z

# PR #1122 — quorum met by a bot that filed nothing, and the only bot that reviews was rate-limited

Routed from `truthful-signals` under the three-way rule (PR/review subject). First-party from the run's
own `automatic-review` step; **not re-derived by this orchestrator** — `ci pr comments --pr-number 1122`
was NOT run, so treat the per-bot states as the step's report, not as an independent measurement.

## The observation

`automatic-review` recorded **"quorum met (participation only)"** with:

- **CodeRabbit — never reviewed ANY head. Rate-limited.**
- **pr-agent — `participated_but_empty`.**
- **sourcery — `participated_but_empty`.**

The required set for this project is **`pr-agent` alone** (`required_bots='pr-agent'`,
`bot_lists_provenance='answered'`). ⇒ **The quorum was satisfied by a bot that filed nothing**, while
the bot that historically produces the actionable findings never saw the diff at all.

`review-retrospective` independently returned **`verdict unmeasurable`** — there was no review substance
to compare. **Two mechanisms agreed there was nothing there, and the merge gate still read green.**

## Why this is yours and why it is not just a repeat

`PLAN-TRUTH-061` shipped a coverage-shortfall disclosure for exactly this shape. **This is that shape
occurring on a later PR**, so it is evidence about whether the shipped disclosure fires where it should
— which is your surface, not ours. Two specific things to check against it:

1. ⛔ **`participated_but_empty` vs `reviewed`.** A participation state is not a review verdict, and the
   barrier is explicitly not a review-quality gate. But if the disclosure treats
   `participated_but_empty` as participation, it will report **full coverage on a PR where nothing was
   reviewed**. That is the *false-clean* direction, and it is worse than the false-alarm direction this
   epic already flagged in 061's roster-vs-required denominator bug.
2. ⛔ **`rate_limited` is a distinct state and must not collapse into "did not participate".** A bot
   that was *prevented* from reviewing and a bot that *chose* not to are different facts with different
   remedies — the taxonomy-collapse failure both epics keep filing. ⚠ #1118 (*automatic-review: add
   stale and not-triggered taxonomy members*) landed on main the same evening; **check whether
   `rate_limited` is in that taxonomy or fell outside it.**

## What we are NOT claiming

- ⚠ We did **not** verify the per-bot states independently. Only `ci pr comments` is evidence of
  participation, and it was not run for #1122.
- The operator **accepted the thinness knowingly** — this is not a report of an unnoticed failure. The
  question is whether the *mechanism* would have disclosed it had nobody been watching.
- ⭐ Standing context, unchanged: a required set of **exactly one** has **no redundancy**. This PR is the
  clearest instance yet — the single required bot returned empty and the gate still passed.

## Nothing owed back

Recorded on our side in `landings/PLAN-TRUTH-060.md`. No plan staged here; the surface is yours.
