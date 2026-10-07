envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T06:10:54Z

component=automatic-review
category=bug
created=2026-07-29

# A review bot's green CHECK can coexist with an explicit refusal to review

On PR #1044 the CodeRabbit CHECK reported SUCCESS while CodeRabbit had explicitly
REFUSED to review. Its comment was updated at 05:23 after the force-push, named
the rebased range `8e49ed0..f02f2645`, and still read "Review limit reached, next
review available in 23 minutes". A green check with zero review behind it.

This is a strictly harder surface than candidate-lesson 009 (which covers
`0 actionable comments` not meaning a clean review). A consumer that has already
learned to distrust comment COUNTS is still misled here, because the CHECK STATE
— the coarsest, most-trusted, most-automatable signal in the whole finalize gate
— is the thing that is lying. Check states lie in both directions: this run also
produced the inverse earlier in the epic's history (a detected refusal reported
as a clean review).

A related flag-shape defect sits next to it, though it did NOT block verification:
`ci pr comments --pr-number 1044 --plan-id ...` was rejected with exit 2 at
22:37:06Z (`ci.py: error: unrecognized arguments: --plan-id`). The orchestrator
retried immediately with `--project-dir` and that call SUCCEEDED, returning all
comments — that successful retry is precisely how the two refusals were
established first-party and surfaced to the operator before the merge decision.

**Correction (recorded by the orchestrator).** The first draft of this message
claimed the call "was never retried with the correct flag shape" and that
evidence-of-participation "failed silently". Both are FALSE. The retry happened
in the very next tool call and succeeded, and the refusals were reported to the
operator, who then made an informed merge-now decision. The retrospective read
the exit-2 line in the script log without reading the adjacent successful call —
a same-archetype error to the one this very message is about: it drew a confident
conclusion from a partial signal. The verb-scoped-flag defect is real and worth
fixing; the "verification never happened" claim built on top of it was not.

`automatic-review` WAS force-marked done — its display_detail reads
"1 comment(s) found (unified triage pending) - forced done" — but that force was
a deliberate, logged choice against sourcery's unresolvable hard quota, taken
with the participation facts in hand, not a fallthrough from a failed check.

## Impact

A review bot's check conclusion is NOT evidence that a review happened. Only the
bot's actual posted comment content is. Two consequences: (1) the finalize gate
must derive participation from `ci pr comments` output, never from check
conclusions, and a failed/rejected `ci pr comments` invocation must BLOCK rather
than fall through to a forced done; (2) `ci pr comments` takes `--pr-number` and
does not accept `--plan-id` — the verb-scoped-flag archetype struck the single
call whose success mattered most.
