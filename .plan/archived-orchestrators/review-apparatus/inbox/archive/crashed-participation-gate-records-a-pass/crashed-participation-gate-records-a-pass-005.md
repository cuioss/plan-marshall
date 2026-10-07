envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:05:38Z

component=plan-marshall:workflow-integration-github
category=bug
bundle=plan-marshall

# github_re_review counts a bot's refusal ACK as a match, and the caller then reports a fresh review that does not exist

On PR #1070, `github_re_review` returned **`matched: true` AND `refusal_detected: true` in one envelope**. The signal that produced the match was CodeRabbit's acknowledgement text — "does not re-review already reviewed commits". That ACK is a refusal notice, not a review.

`automatic-review/SKILL.md` then tells the caller "the fresh review is now on the PR". That statement is **false** in exactly this case, and it is emitted with no caveat, so the caller has no way to tell an actual re-review from an acknowledged refusal.

Two defects, one envelope:

1. The matcher accepts an ACK as evidence of a review.
2. The two returned fields are mutually contradictory, and no consumer contract says which one wins.

This is PLAN-PR-008 territory and was deliberately not fixed in PR #1070.

## Solution

- Exclude refusal-ACK text from the re-review match population. A comment whose body is the bot's own auto-generated re-review refusal is never a match.
- Make the envelope self-consistent: when `refusal_detected` is true, `matched` MUST be false. Encode that as an invariant with a test, not as caller-side prose.
- Correct the `automatic-review/SKILL.md` success narrative so it cannot claim a fresh review is on the PR when the underlying signal was a refusal.

## Impact

The consuming gate treats `matched: true` as clearance for the review loop-back. An ACK-as-match therefore clears a loop-back that nothing satisfied, which lands the PR with an unreviewed HEAD while every surface reports the review as delivered.
