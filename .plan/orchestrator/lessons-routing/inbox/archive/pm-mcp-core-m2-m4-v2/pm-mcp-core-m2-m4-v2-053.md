envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-21T16:19:56Z

component=plan-marshall:automatic-review
category=improvement
created=2026-11-21
bundle=plan-marshall
title=Recover a stale-notice quota refusal in automatic-review without an operator loop

# Recover a stale-notice quota refusal in automatic-review without an operator loop


## Context

On PR #542 the required review bot coderabbit posted a free-tier quota refusal ("resets in about 26 minutes"). With `review_rate_window_await: false` in the step params, automatic-review settled the refusal and returned `loop_back` twice (iterations 1 and 2), even though by iteration 2 the stated window had already elapsed. Only after an operator answered "Re-ask CodeRabbit" did iteration 3 run `recovery-action` -> `trigger_stale_notice`, post the trigger once, and receive a full review on HEAD.

## Root cause

The stale-notice recovery (`trigger_stale_notice`) is only reached when the rate-window path is armed or an operator intervenes; with the await knob off, an elapsed refusal window is treated the same as a live one and the step loops back unchanged.

## Proposed action

When a required bot's refusal is `refused_awaitable` and its stated window has already elapsed, run the `trigger_stale_notice` recovery on the same pass regardless of `review_rate_window_await`, and loop back only if the re-review still does not arrive. Alternatively default `review_rate_window_await` to true for required bots.

## Evidence

- aspect: chat_history_analysis — two automatic-review loop-backs with identical `refused_awaitable` state, the second noting "the 26-minute window has already elapsed"
- aspect: log_analysis dispatch_boundaries — 3 `returned_with_findings` rows in 6-finalize
- aspect: plan_efficiency — 6-finalize holds 53% of 5.03M tokens; `github_re_review` call of 553 s
