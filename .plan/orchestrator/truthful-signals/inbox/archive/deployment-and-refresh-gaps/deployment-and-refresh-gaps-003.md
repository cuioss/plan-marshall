envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:34Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `outbound-hostname-verification-core` (PR #689), original message `outbound-hostname-verification-core-003.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

# Candidate lesson: a rate-limited review bot is not recovered by re-firing the review step

**Component:** `plan-marshall:automatic-review`
**Category:** improvement
**Evidence:** decision log `ba3351` (15:08), `b9a05a` (15:49)

## What happened

CodeRabbit posted a "Review limit reached — next included review available in 22 minutes"
notice on PR #688 at 14:14:48. It had enumerated all 17 files and the `09473852..46102d78`
range, so it *saw* the PR — it simply could not spend a review.

`automatic-review` resolved this as `refused_awaitable` with cause `quota` and returned
`loop_back`, admitting iteration 1 of 6.

## Why the loop-back could never have worked

**CodeRabbit does not auto-review after its window resets, and it does not re-review a PR it has
already refused.** The refusal comment stays on the PR. A `loop_back` re-fire re-reads that same
stale refusal and classifies the bot as refused again — so all 6 iterations would have burned
against a ceiling with zero chance of the state changing.

The refusal is **time-based**, and the loop-back mechanism is **event-based**. They do not meet.

## What actually worked

Closed PR #688 **without merging** and opened replacement PR #689 on the same branch and the
same HEAD (`46102d78`), with the PR body copied verbatim. The fresh PR claimed the now-open reset
window and got a real review. `#688` remains closed-not-merged so its review history stays
readable for audit; `references.pr_number` was updated 688 -> 689.

## Rule

When a required review bot returns `refused_awaitable` with cause `quota`:

- Do **not** re-fire the review step on the same PR. Confirm first whether the bot re-reviews
  after a window reset — CodeRabbit does not.
- Either wait out the window and then **replace the PR** (close-without-merge + reopen on the
  same branch/HEAD), or arm the rate-window claim (`review_rate_window_await`, which was `false`
  for this plan, so no automatic recovery was armed).
- Note the interaction with `pre_merge_comment_barrier=fail_into_loopback`: the barrier
  re-derives participation independently and refuses until the bot is proven, so recovering the
  review is **required for the merge**, not merely preferred. There is no "skip it" path.

## Related coverage note worth carrying

At the point of the refusal, actual review coverage was far weaker than the raw comment count
suggested: pr-agent participated, CodeRabbit examined nothing, and Sourcery's "participation"
was itself a budget-exhausted refusal notice (a refusal notice is still a review *body*, so it
classified as participated). One of three bots had actually read a TLS-relaxing diff. Comment
count is not coverage.
