envelope_version=1
sender_type=plan
sender_id=cross-repo-telemetry-archive-and-analyze
epic=post-run-quality
kind=candidate-lesson
created=2026-10-03T23:21:35Z

component=plan-marshall:automatic-review
category=bug

# Hand the review-bot rate-window await to the orchestrator instead of blocking a leaf

## Context

The automatic-review dispatch at 21:19:50Z on PR #1694 hit CodeRabbit's hourly quota (refusal cause quota, "0 remain"). With review_rate_window_await=true it armed refusal recovery at 21:31:14Z (claimed the coderabbit rate window, seconds_remaining=3600, attempts 1/6) and then waited inside the dispatched leaf. It produced no completion line and no dispatch-boundary row, and the orchestrator stopped it after more than an hour. A fresh dispatch at 22:46Z finished the step in about 4 minutes.

## Root cause

The rate-window recovery runs its await synchronously inside the execution-context leaf, bounded by review_rate_window_timeout_seconds (3600) times up to 6 attempts. A leaf has no wake path and the orchestrator cannot observe progress, so a quota window turns into an unobservable multi-hour block.

## Proposed action

When recovery needs a wait longer than a short bound, return a signal (window ETA, claim id) to the orchestrator and let the orchestrator-tier await-long-running seam own the wait and the re-dispatch, as the long-running-wait contract already prescribes for result-bearing waits.

## Evidence

- decision.log 21:31:06Z / 21:31:14Z - quota refusal routed into recovery; window claimed, seconds_remaining=3600, attempts=1/6
- work.log - [SKILL] load at 21:19:50Z with no matching completion line; next automatic-review load at 22:46:24Z
- aspect: logging_gap_analysis - stopped dispatch recorded no boundary row
- manifest step_params: review_rate_window_timeout_seconds=3600
