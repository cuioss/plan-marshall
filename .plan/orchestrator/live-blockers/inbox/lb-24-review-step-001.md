envelope_version=1
sender_type=plan
sender_id=lb-24-review-step
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T11:57:27Z

component=plan-marshall:automatic-review
category=bug

# Re-trigger a required bot whose quota notice window already elapsed

## Context

On PR #1742 (plan lb-24-review-step, the plan that rewrote this recovery) the first automatic-review pass met a CodeRabbit quota notice written at 20:16:16Z stating a 6-minute reset. The pass read it at about 21:14Z, so the notice was stale. The recovery selector answered `settle_stale_notice` / `notice_window_elapsed`: no claim, no wait, no trigger. Trigger B had nothing to trigger (a refused bot is neither stale nor has stored findings), so the step looped back and a re-dispatch would have met the same stale notice. The main context improvised the recovery: waited about 31 minutes, posted `@coderabbitai full review` via `re-review --escalated` (CodeRabbit answered with a fresh 53-minute rate limit), waited 90 more minutes, and posted the escalated command a second time before a review ran.

## Root cause

`settle_stale_notice` treats an elapsed window as "nothing to do" for a required bot that has not reviewed. Nothing on that path asks the bot again, so the participation guard can only loop until the ceiling. The self-review had already flagged this route as a dead end (`recovery_route_dead_end` at github_re_review.py:910) and graded it advisory.

## Proposed action

For a required bot whose notice is stale, return an action that triggers the bot (ordinary or escalated command, capped by the rate-window attempt counter) instead of settling, and let item 7a own any further wait. Add a test where a stale notice on a required bot leads to exactly one trigger.

## Evidence

- decision.log 2026-10-09T21:14:30Z: refusal recovery NOT ARMED, notice stale (written_at 20:16:16Z, eta_seconds 360)
- decision.log 21:15:42Z, 21:56:30Z, 23:27:21Z: manual waits and two escalated posts by the main context
- work.log: no entry between 21:14:49Z and 23:27:22Z
