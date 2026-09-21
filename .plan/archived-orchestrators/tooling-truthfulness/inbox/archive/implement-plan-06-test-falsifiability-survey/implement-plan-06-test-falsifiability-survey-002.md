envelope_version=1
sender_type=plan
sender_id=implement-plan-06-test-falsifiability-survey
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-12T22:05:47Z

# Candidate lesson (recurrence): Trigger-B single-bot selection leaves the other required bot stale

Related lesson: 2026-09-06-07-003 (Trigger-B selects one bot by newest
finding and cannot reach a different stale bot)
component=plan-marshall:automatic-review
category=bug
source_plan=implement-plan-06-test-falsifiability-survey
source_pr=1476

## Observation

After a loop-back fix commit advanced HEAD to 2356d28fa, trigger-B selected
coderabbit (newest finding's bot) and left required cuioss-review-bot stale;
the pre-merge barrier's predicate 2 would have blocked on its staleness
indefinitely. Worked around by invoking the documented `github_re_review
re-review` verb for cuioss-review-bot with identical args — an explicit
trigger is its only re-review path — and it answered with an in-place update
naming the HEAD verbatim.

Second half: that in-place update arrived as `matched: true` /
`head_sha_verified: false`, which the trigger-B arm reads as an
incremental-review decline. It is not a decline — the body states "Review
updated until commit {sha}" — it is the known issue-comment-path
discriminator defect (lesson 2026-09-08-22-001) firing on a completed review.
A decline disposition here would accept away a review that actually happened.

## Suggested disposition

Merge into 2026-09-06-07-003 as a recurrence (extends the filed trigger-B
limitation with the cuioss half), and cross-link 2026-09-08-22-001 for the
decline-misread half.
