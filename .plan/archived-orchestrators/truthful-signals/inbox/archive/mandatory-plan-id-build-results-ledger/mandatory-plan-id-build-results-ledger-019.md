envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T07:20:20Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
title=refused_awaitable plus a pending check means the review is IN FLIGHT, not that none is coming
forward_to=review-apparatus

# `refused_awaitable` plus a pending check means the review is IN FLIGHT

**CROSS-EPIC — belongs to `review-apparatus`** per the three-way routing rule (this is a
PR/review-participation finding, and the PR test wins outright). Filed here for forwarding;
do not action locally.

## What happened

On PR #1075 (`mandatory-plan-id-build-results-ledger`) the merge **outran a real review by
3 minutes 23 seconds**.

| Time (UTC) | Event |
|---|---|
| 2026-08-01 20:22:05 | Sourcery refuses |
| 2026-08-01 20:39:50 | `automatic-review` classifies coderabbit=`refused_awaitable`, sourcery=`refused_hard` |
| 2026-08-01 21:17:06 | Operator merge-gate decision: proceed at 1-of-3 coverage |
| **2026-08-02 06:24:23** | **`branch-cleanup` stops the CI wait** |
| **2026-08-02 06:24:46** | **squash-merge lands as `b5477589c`** |
| **2026-08-02 06:28:09** | **CodeRabbit posts 8 actionable + 1 outside-diff + 5 nitpick comments** |
| 2026-08-02 06:37:42 | merge lock released |

One of those 14 comments is a **MAJOR live regression** in code this plan's own finalize
step introduced.

## The reasoning error, precisely

The 06:24:23 decision log entry is *correct on its stated premise*:

> `ci checks` wait would block indefinitely: `overall_status=pending` is caused SOLELY by the
> CodeRabbit check, the bot that already published a rate-limit refusal. Every substantive
> check passes... This is the check-state-lies pattern in the blocking direction — a refused
> bot leaves its check pending forever.

The diagnosis is right: **that check** would never turn green. The inference drawn from it is
wrong: **therefore no review is coming.**

`refused_awaitable` is a classification that literally means *the refusal is retryable and a
later attempt will produce real coverage*. The run's own `review-retrospective`, written at
21:20 the previous evening, said so explicitly in its carry-forward:

> CodeRabbit's refusal is `refused_awaitable`. If a post-merge re-review is run once the
> rate-limit window clears, this PR's diff would get its first real independent read. The
> green CodeRabbit check-run should not be allowed to suppress that follow-up.

That prediction was correct and was recorded ten hours before the merge. The merge path did
not consult it.

## The compounding config

`review_rate_window_await: false` was set, which disabled the one mechanism that would have
waited out the rate-limit window. The `automatic-review` warning at 20:39:50 named this at
the time: *"review_rate_window_await=false so no recovery was driven."* The window did clear
— roughly ten hours later — and the review that followed was substantive.

`pre_merge_comment_barrier: fail_into_loopback` was also configured, but a barrier evaluated
**once**, 23 seconds before the merge, is not a barrier against a comment that arrives 3
minutes after it.

## Do this instead

- **Separate the two propositions.** "This check will never turn green" and "no review is
  coming" are different claims with different evidence. A refused bot's stuck check proves
  only the first.
- **`refused_awaitable` must not be merge-passable without an explicit awaited retry or an
  explicit operator override that names the awaitability.** The classification carries the
  remedy in its own name; discarding it silently is the defect.
- **Re-evaluate the comment barrier after acquiring the merge lock**, not before the wait is
  abandoned. The gap between "decide to merge" and "merge lands" is where an in-flight review
  arrives.
- When the run's own `review-retrospective` records a carry-forward prediction, the merge path
  should read it. On this PR the prediction was written, was correct, and was ignored.

## Related

This is the third distinct polarity of the check-states-lie family:
1. green check, no review (CodeRabbit's `completed: true` while publishing a refusal);
2. pending check that will never clear (this one, in the blocking direction);
3. **pending check that will never clear while the review it belongs to is genuinely in
   flight** — the new one, and the one that let a MAJOR finding land in main.
