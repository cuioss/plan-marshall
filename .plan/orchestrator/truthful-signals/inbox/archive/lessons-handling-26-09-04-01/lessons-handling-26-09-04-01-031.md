envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T06:45:29Z

component=plan-marshall:automatic-review
category=bug

Relayed from Token-Sheriff PLAN-10 (PR #725 / `6953b03c`). ⚠ Note the timing is exact and recorded: the FIND window closed at 18:13:09Z and the rebuttal landed at 18:28:23Z — the producer had stopped looking ~15 minutes earlier, so a reviewer's rebuttal to a WRONG disposition was never filed and surfaced only because a human went looking by hand. ⛔ Companion to `-030`: that message records the wrong dismissal, this one records why the correction nearly did not arrive.

# A reviewer's rebuttal landed after the FIND fetch window closed, so the comment was never filed and would have shipped unhandled

**Proposed component**: `plan-marshall:automatic-review`
**Proposed category**: `bug`
**Plan**: `refresh-2a-coverage-priorities` (PR #725, merged)
**Evidence**: finding `5b35ad` (Q-Gate, phase `6-finalize`), second recorded process failure

## What happened

Iteration 1 of the automated-review FIND stage ran at **18:13:09Z** and closed
its fetch window. CodeRabbit's rebuttal to the disposition of finding `97b350`
(review comment 3961018824) landed at **18:28:23Z** — roughly fifteen minutes
after the producer had stopped looking.

The consequence: the rebuttal was **never filed as a finding**. The pipeline had
no record of it. It surfaced only because the re-review verification went looking
for it by hand.

That matters here because the rebuttal was correct and the disposition it
rebutted was wrong (see the companion candidate-lesson on the JLS claim). Had the
manual re-review not gone looking, PR #725 would have merged carrying production
Javadoc asserting a compile-time guarantee the code did not have.

## The structural defect

The wait region treats "the fetch window closed" as equivalent to "the reviewer
has finished". Those are different facts:

- A bot that has posted its **initial** review may still post **follow-ups** in
  response to the dispositions the run transmits back.
- The transmit-then-close shape means the run posts responses and then stops
  observing, which is precisely the moment a reviewer is most likely to reply.
- A dismissal (`REJECTED` / false-positive) is the disposition most likely to
  draw a rebuttal, and also the one whose reasoning nothing else re-checks.

So the highest-risk disposition class is the one the closed window is most likely
to drop.

## Candidate corrective directions

Offered as directions for the epic to judge, not as a settled fix:

1. After transmitting dispositions, **re-open a bounded fetch window** rather
   than treating the pre-transmit fetch as terminal — at minimum when any comment
   was dispositioned as rejected/false-positive.
2. Make "no new comments since transmit" an **observed** fact carried in the
   step's return, rather than an inference from the window having elapsed. The
   distinction is the familiar *which kind of zero is this* rule: "I looked after
   transmitting and found nothing" is not the same as "I stopped looking before
   the reply could arrive."
3. Treat a **post-transmit reviewer reply on a rejected finding** as a
   first-class signal that re-opens the finding, rather than as new unrelated
   input.

## Why this is not covered by lesson `2026-09-08-18-001`

`2026-09-08-18-001` is also filed against `plan-marshall:automatic-review`, but
it records a **documentation/argparse drift** — SKILL.md prose naming
`--enabled-bots` / `--settled-bots` where the live surface declares
`--participated-bots` / `--refused-bots`. This candidate is a **timing/coverage**
defect in the wait region: a real reviewer comment that the pipeline never
observed. Fixing the flag names does not close it, and the two should not be
merged.
