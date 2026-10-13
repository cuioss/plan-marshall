envelope_version=1
sender_type=plan
sender_id=lb-33-leaf-test-scope-and-executor
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T19:58:43Z

component=plan-marshall:automatic-review
category=improvement
confidence=high
source_aspects=chat_history_analysis,permission_prompt_analysis

# Hand the rate-window wait back to the orchestrator instead of polling in a leaf

## Context

On lb-33, CodeRabbit's hourly quota refused a review twice. The first time, the dispatched automatic-review leaf claimed the rate window (3600 s, attempt 1/6), then could not run Branch 3's paced poll: the harness blocked the standalone `sleep 60`, and the Monitor tool is not available to a leaf. A 3600 s window is also beyond the step's 900 s FIND budget. The leaf returned `blocked` / `rate_window_poll_unpaceable`, leaving the claim held, and the orchestrator had to work out the continuation by hand. On the final head the second refusal (ETA about 54 min) ended in an operator merge without that review.

## Root cause

The Rate-limit refusal recovery section assumes the step can wait out the window inside its own envelope. A dispatched leaf has no sanctioned long wait; only the orchestrator-tier await-long-running seam has one.

## Proposed action

Make Branch 3 return a structured wait signal (claim expiry, attempts remaining, resume entry point) that the orchestrator honours through await-long-running before re-dispatching from the jittered-wake boundary, and document that a leaf never polls a rate window itself.

## Evidence

- aspect: chat_history_analysis — leaf return `status: blocked, reason: rate_window_poll_unpaceable, claim_expires_at 2026-10-10T12:54:15Z`; later `required_bot_rate_limited` with ETA about 17:30Z
- aspect: permission_prompt_analysis — "Harness blocked the paced sleep ('use Monitor'); Monitor is not available to a leaf"
