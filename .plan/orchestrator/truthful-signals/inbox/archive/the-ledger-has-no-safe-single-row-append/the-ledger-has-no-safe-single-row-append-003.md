envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:18Z

component=plan-marshall:automatic-review
category=improvement
confidence=high

# Read the limit notice before triggering - a trigger re-arms the window

## Context

The run fired six explicit `@coderabbitai review` triggers at 11:52Z, 14:25Z, 16:48Z, 18:52Z, 21:00Z and 21:30Z. Every one was acknowledged; none produced a review. The rate-limit ETA readings across the run were 57, 44, 27, 50, 2 and 45 minutes.

Two of those transitions are the evidence. After the fourth trigger the ETA ROSE from 27 to 50 minutes. Then at approximately 21:30Z, with the window down to 2 minutes, a single trigger was fired and the window re-armed to 45 minutes. That second one is a controlled observation: the window had almost elapsed, exactly one action intervened, and the window re-armed.

This creates a genuine bind. CodeRabbit declares `requires_explicit_trigger` with no push trigger, so it will never review without a trigger; yet every trigger re-arms the window the caller is waiting on. Trigger-and-wait cannot converge.

## Root cause

The remedy for a stale review (post a trigger) and the remedy for a closed rate window (wait) are in direct conflict for a bot that both requires an explicit trigger and rate-limits triggers. Firing the two remedies in combination is worse than either alone, and no rule ordered them.

## Proposed action

Before firing a re-review trigger at a bot whose `rate_limit_class` is `awaitable_window`, read the persistent limit notice first and trigger ONLY if it has cleared. A trigger fired into a closed window costs budget and buys nothing. Record the observed re-arming behaviour in the bot's registry data so the ordering rule has a declared basis rather than being rediscovered per run.

## Evidence

- decision.log 2026-09-06T19:29:06Z — "STRATEGY CORRECTION - triggering is counterproductive ... The ETA sequence across attempts is 57 -> 44 -> 27 -> 50: it was DECREASING toward a reset and then ROSE after the fourth trigger."
- decision.log 2026-09-06T21:46:39Z — "CONFIRMED: each @coderabbitai review trigger RESETS the rate window ... The 2min->45min transition happened across a single trigger fired at ~21:30Z, which is a controlled observation."
- decision.log 2026-09-07T02:19:32Z — six triggers, none produced a review; a 45-minute wait with NO trigger produced no delayed review either, refuting the slow-delivery hypothesis.
