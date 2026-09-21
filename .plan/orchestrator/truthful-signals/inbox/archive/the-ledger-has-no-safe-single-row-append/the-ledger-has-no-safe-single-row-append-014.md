envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:23Z

component=plan-marshall:automatic-review
category=anti-pattern
confidence=high

# Do not infer a plan-tier cause for a stall - read the persisted envelopes

## Context

When the replacement PR #1434 received its review within fifteen minutes, the run recorded a causal conclusion at 2026-09-07T03:12:08Z:

> This confirms the block on #1424 was that PR's exhausted free-OSS review budget ... reviewing the full 7-file diff ... under plan=Team with NO limit notice.

Two later observations contradict it. At 06:05:48Z the same run noted of the #1434 review that "Its hourly budget footer reads 0 remaining" — so the limit notice was there after all. And the review retrospective, reading the persisted review bodies, found that all three CodeRabbit envelopes across both PRs record the same `Plan: Team` and the identical footer "0 remain after this review".

The remedy worked. The story attached to it was wrong, and neither later entry referenced the earlier claim, so the contradiction sat unreconciled in the same run's own record.

The better-evidenced mechanism was already available: every trigger re-arms the rate window (ETA 57, 44, 27, 50, 2, 45 minutes, with a controlled 2-to-45 transition across one trigger). A fresh PR is reviewed automatically and therefore needs no trigger and re-arms no window. That explains the outcome without any plan-tier claim.

## Root cause

A dramatic success invites a causal story, and the cheapest available story was a tier difference nobody checked. The persisted envelopes were on disk the whole time and were not read until the retrospective step read them.

## Proposed action

Do not attribute a reviewer stall to a plan tier, quota class, or account state without reading the persisted review envelopes for that claim. When a recreate-style remedy succeeds, record what changed mechanically (no trigger required, no window re-armed) rather than inferring an account-level cause. A wrong causal story about a reviewer stall is re-applied as a remedy on the next stall, which is what makes it expensive.

## Evidence

- decision.log 2026-09-07T03:12:08Z — the plan-tier claim, made live.
- decision.log 2026-09-07T06:05:48Z — same run, same PR: "Its hourly budget footer reads 0 remaining".
- review-retrospective.md § "A stated premise this store does not corroborate" — all three envelopes record `Plan: Team` and "0 remain after this review".
- decision.log 2026-09-06T21:46:39Z — the trigger-re-arms-the-window mechanism, which survives the refutation.
