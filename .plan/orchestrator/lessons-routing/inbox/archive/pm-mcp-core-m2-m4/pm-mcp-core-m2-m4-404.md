envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-11-07T14:28:23Z

component=plan-marshall:automatic-review
category=improvement
source_plan=pm-mcp-core:plan-v2-98-optional-conversion-workflow

# Add escalate_ask reasons for window_open and quota refusals when await is off

## Context

In 6-finalize of pm-mcp-core PLAN-V2-98 (PR #309) the review-bot refusal handling needed an operator decision. The review step docs' `escalate_ask` reason vocabulary has no value for a `window_open` refusal, nor for a quota refusal when `review_rate_window_await=false`. With await off the contract formally skips the Branch 0 recovery section and says to treat the refusal as an ordinary settle; the leaf returned `refusal_structural` "anyway" because looping back would repeat the same state forever.

## Root cause

The reason vocabulary only covers the structural (size) refusal and the await-enabled rate-window path; the await-disabled quota/window refusals have no named exit, so a leaf must either misname the reason or loop.

## Proposed action

Add named `escalate_ask` reasons (for example `refusal_window_open` and `refusal_quota_await_off`) with their prompt options, and state in the step docs which branch a refusal takes when `review_rate_window_await=false`.

## Evidence

- aspect: chat-history-analysis - automatic-review leaf return "refusal_structural ... I returned the structural variant anyway"
- status.metadata.halts.6-finalize.automatic-review reason `escalate_ask{reason: refusal_structural}`
- operator report at finalize
