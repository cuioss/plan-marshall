envelope_version=1
sender_type=plan
sender_id=the-foreign-gate-population-and-branch-f-recovery
epic=review-apparatus
kind=candidate-lesson
created=2026-09-13T08:20:22Z

component=plan-marshall:automatic-review
category=improvement

# The review-quota window priced in-run remediation of review-apparatus defects out of reach, so two live defects shipped as carry-forward

This is the cost half of the two carry-forward candidates (`852b0f`, `658eec`), and it is
the reason they are carry-forward rather than fixed.

## What the run paid

PR #1473 paid THREE separate CodeRabbit quota refusals, each answered with a ~90-minute
wait — roughly four and a half hours of wall clock on one PR, on top of the four review
rounds that did complete. Every completed review's own footer confirmed the ceiling:
"Your plan provides up to 1 included review per hour; 0 remain after this review."

## The structural consequence

Because the mandatory-review cycle restarts whenever HEAD advances, **any fix costs a full
quota window**. Two live defects in the review apparatus itself (`852b0f`, a false green on
the merge-gating participation predicate; `658eec`, a refusal invisible to
`wait-for-comments`) were both one-file changes, and both were ACCEPTED unfixed on exactly
this reasoning: the cost of the extra round was not proportional to a defect no consumer had
acted on. The run reached the correct decision, and the decision still shipped two known
defects to main.

That is the observation worth carrying: for defects in the review apparatus, the review
apparatus's own throughput ceiling is what decides whether they get fixed in the run that
found them. A defect found at iteration 8 is systematically less likely to be fixed than the
identical defect found at iteration 2 — not because it is smaller, but because HEAD has
already been advanced enough times.

## Second observation, same run

Every detector that operates on comment ENVELOPES agreed nothing was wrong while three
distinct refusals were live: `wait-for-comments`' `rate_limited_bots[]` (missed the refusal
entirely), `movement_matched_bots[]` (empty), and `review_completeness`' currency arm
(reported `participated` over an explicit refusal). The only detector that was right all run
was READING THE COMMENT BODY. The compensating practice carried the run; the automation did
not.

## Adjacent corpus entries for dedup

- `2026-09-05-07-008` — "CodeRabbit's allowance is contended fleet-wide: fire one pre-staged
  trigger at the stated reset." The scheduling response to the same ceiling.
- `2026-09-03-23-002` — "CodeRabbit's rate-limit ETA is unparseable and its window slides."
  The clock half.

Neither carries the point above, which is about what the ceiling does to the FIX decision
for review-apparatus defects specifically. If the epic already prices this, treat this
message as corroboration rather than a new item.

Source: plan `the-foreign-gate-population-and-branch-f-recovery`, PR #1473 (merged
`38af136ede5c7d6ea531a38d59a67ece1bf3ade2`).
