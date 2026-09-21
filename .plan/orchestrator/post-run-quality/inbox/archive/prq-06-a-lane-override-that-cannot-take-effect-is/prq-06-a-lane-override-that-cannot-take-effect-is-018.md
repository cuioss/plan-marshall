envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:47:01Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement

# Four self-review rounds were forced by a may_close predicate and then retroactively judged superseded

The self-review's round-closing condition produced four separate `further_round_owed` findings on this plan. Every one of them was later resolved not by fixing anything, but by recording that a subsequent round had superseded it. Four rounds of full-cost dispatch bought four notes saying the round need not have been owed.

## Evidence (all 6-finalize, `further_round_owed at pre-submission-self-review`)

| hash | why the round was owed | how it was resolved |
|---|---|---|
| `91b12f` | "findings returned so no close" | `accepted` — "superseded by round 3's full-surface clean pass" |
| `6611db` | "findings returned, so the round cannot close" | `accepted` — "superseded by round 3's full-surface clean pass" |
| `8437fc` | "may_close no because findings were returned" | `taken_into_account` — "superseded by round 8 full-surface confirmation round" |
| `75f683` | "findings returned so round cannot close" | `taken_into_account` — "superseded by round 8 full-surface confirmation round" |

A fifth, `5e9ee0`, is the benign form of the same predicate: a delta round verified clean but `may_close=no` **because it was a delta round**, so a full-surface confirmation was owed and duly ran.

## The pattern

The predicate is "this round returned findings, therefore another round is owed." That is sound in isolation but composes badly: it fires once per round, and each firing is resolved by the NEXT round rather than by any action. Two resolution texts are identical across pairs, which is the signature of a predicate producing bookkeeping rather than information.

## Rule / question for the epic

`5e9ee0`'s shape (delta round clean, full-surface confirmation owed) is genuinely load-bearing — it is what prevents a delta pass from closing on a partial surface. The four above are not: they record that a round which found things did not also close, which is already implied by the loop continuing.

Worth deciding: should `further_round_owed` be filed as a Q-Gate FINDING at all when its only resolution is "a later round superseded it"? A loop-control fact is not the same object as a defect, and filing it as one puts four no-op rows through the triage surface and into every downstream count.

This connects to the separately-reported finalize cost (50% of 8.44M tokens, 47 firings over 9 steps, 7 of `pre-submission-self-review`'s 8 prior firings returning `loop_back`). The token finding names the expense; this names one predicate driving it.
