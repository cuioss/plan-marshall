envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T10:23:49Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-10-18

# Scope review re-fires to the delta when it changes no executable code

## Context

In plan-20-job-runner the 6-finalize phase took 11.46M of 17.73M tokens (65%, a floor because the phase is still open). The security audit fired 16 times, the functional review 11 times and the code review 9 times; 37 finalize dispatches were recorded, 10 of them returning findings. Many re-fires followed commits that changed only Javadoc, ADR or developer-guide text (fe92818, 7013898, 84c76e4, 1855f7d), and each still cost a full dispatch: about 50 to 65K tokens per security re-fire and a full functional-review round over all 11 deliverables.

## Root cause

A new HEAD invalidates every review step's record, and the re-fire decides only inside the leaf whether the delta matters, after the envelope, skill loads and footprint resolution have already been paid for. There is no deterministic pre-check of what class of file the delta touched.

## Proposed action

Before re-firing a review step, diff its `head_at_completion..HEAD` with a script and classify the delta (code / test / docs-only / comment-only). For a docs-only or comment-only delta, let the security audit carry its prior record forward with the delta noted, and let the functional and code reviews run a delta round over the changed files only instead of a full round.

## Evidence

- aspect: plan_efficiency - max_phase_token_share 0.65, dominant phase 6-finalize=11459781; [BUDGET] error at 17.7M vs the 2.5M multi_module+feature anchor
- aspect: chat_history_analysis - security re-fires at fe92818, 7013898, 84c76e4, 1855f7d each report a comment-only delta and "0 edits, 0 findings"
- aspect: llm_to_script_opportunities - delta classification proposed as a low-complexity script
