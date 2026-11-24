envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-21T09:47:08Z

component=plan-marshall:automatic-review
category=improvement
created=2026-11-21
bundle=plan-marshall
title=Arm the review rate-window await before the first round when the required bot is on a free tier

# Arm the review rate-window await before the first round when the required bot is on a free tier

## Context

On PR 530 the required reviewer CodeRabbit answered every round with a free-tier quota refusal. The step spent all 3 of its loop-back rounds (plus one operator-granted round) before a close/reopen as PR 531 got a review. The first two rounds ran with `review_rate_window_await: false`, so a stale `refused_awaitable` notice was settled as an ordinary refusal and nothing re-asked the bot.

## Root cause

With the rate-window await off, an awaitable quota refusal of the required bot can only end in a loop-back; the recovery (trigger, window claim, close/reopen) only started once the operator chose "Re-ask CodeRabbit" in round 3.

## Proposed action

For epics whose required reviewer is on a quota-limited tier, stage plans with `review_rate_window_await: true` (the manifest of this plan shows it true only after the fact), or have the step take the stale-notice recovery arm on the first awaitable refusal instead of looping back.

## Evidence

- aspect: chat_history_analysis - four automatic-review loop-backs, operator decisions "Retry the review", "Re-ask CodeRabbit", "Grant one more round"
- aspect: plan_efficiency - 6-finalize holds 68% of 10.2M tokens
- aspect: log_analysis - slowest script github_re_review 618 s; status.metadata loop_back_budgets automatic-review spent 4, granted 1
