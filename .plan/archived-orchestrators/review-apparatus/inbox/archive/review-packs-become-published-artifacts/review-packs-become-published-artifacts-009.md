envelope_version=1
sender_type=plan
sender_id=review-packs-become-published-artifacts
epic=review-apparatus
kind=candidate-lesson
created=2026-09-03T22:34:16Z

# Carry the review-bot rate-window wait budget instead of taking it conversationally

component: plan-marshall:automatic-review
category: improvement
confidence: medium

## Context

The operator supplied the retry policy for a review-bot rate window in chat, as part of the unattended-run mandate:

> "In case of running in a CodeRabbit quota window. wait (sleep) at least for 90 minutes and try again. Until the upper limit of 10 waits"

The plan's manifest carried `review_rate_window_await: false` with `review_rate_window_timeout_seconds: 3600`. That pair cannot express the policy the operator wanted: a 90-minute-per-attempt wait with a 10-attempt ceiling exceeds a single 3600-second budget by an order of magnitude, and the await is switched off entirely.

`automatic-review` finished `done` with `31 comments, 0 new; coderabbit quota-refused, sourcery size-refused`.

## Root cause

The configuration surface models the rate window as one flat timeout, not as a retry policy with a per-attempt interval and an attempt ceiling. CodeRabbit's limit is one review per hour, so any wait shorter than that interval cannot succeed, and a single 3600-second budget affords at most one attempt at the boundary.

Because the surface cannot express the policy, the operator supplied it in prose — which means it applied to that one run, was not recorded in the manifest, and is not available to the next plan that meets the same window.

## Proposed action

Model the rate window as a retry policy: a per-attempt wait interval and a maximum attempt count, rather than a single aggregate timeout. Default the interval from the bot's known rate limit (one review per hour for CodeRabbit) instead of requiring the operator to know it.

Filed at medium confidence: the observation is solid, but whether the right fix is a richer knob or a bot-registry-derived default is a design choice for the epic.

## Evidence

- aspect: chat_history_analysis — the operator turn quoted above, from the unattended-run mandate
- manifest `step_params.automatic-review` — `review_rate_window_await: false`, `review_rate_window_timeout_seconds: 3600`, `review_completion_poll_timeout_seconds: 600`
- `status.metadata.phase_steps` — `automatic-review` display_detail: "31 comments, 0 new; coderabbit quota-refused, sourcery size-refused", firing_count 2
- The merge ultimately cleared its review barrier through a `barrier-ask-override`, not through completed bot participation
