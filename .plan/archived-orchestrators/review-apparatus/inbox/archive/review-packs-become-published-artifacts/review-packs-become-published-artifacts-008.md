envelope_version=1
sender_type=plan
sender_id=review-packs-become-published-artifacts
epic=review-apparatus
kind=candidate-lesson
created=2026-09-03T22:34:15Z

# Report the token cost of a dispatch that errors and returns nothing

component: plan-marshall:phase-6-finalize
category: improvement
confidence: medium

## Context

One 6-finalize dispatch terminated with `termination_cause: error` at 2026-09-03T16:22:43Z after 918,719 ms and 47 tool uses, having returned nothing. It cost **344,716 tokens** — 8.5% of the whole plan's 4,063,723.

`retryable_total_tokens` for the phase is 0, so this is not a session-restart or harness-cancellation loss that a re-run recovers. Under the current contract, what remains stamped `error` is genuine terminal waste: findings-bearing loop-backs are stamped `returned_with_findings` instead, and the phase records 2 of those separately.

## Root cause

The dispatch-boundary artifact records `error_total_tokens` per phase, and the retrospective's logging-gap aspect reads it — but only after the plan has landed. Nothing surfaces the figure at the time it is spent, so a dispatch that burns a third of a million tokens and returns nothing looks, from the orchestrator's position, like any other failed step to retry.

The distinction the contract is careful to preserve — genuinely-wasted vs retryable spend, never summed into one "failure" figure — is preserved in the artifact and then not shown to anyone until the retrospective.

## Proposed action

Surface `error_total_tokens` on the step-failure path: when a dispatch returns `error`, report the token cost alongside the failure, keeping it distinct from `retryable_total_tokens` so the operator can tell a deterministic dead end from recoverable infrastructure loss.

Filed at medium confidence: the measurement already exists and is correct, so this is a reporting change rather than a defect, and the threshold at which a wasted dispatch warrants operator attention is not established.

## Evidence

- aspect: logging_gap_analysis — 6-finalize `error_total_tokens: 344716`, `retryable_total_tokens: 0`
- aspect: log_analysis — 6-finalize dispatch boundary rows: `error` (344,716 tokens, 47 tool uses, 918,719 ms), `returned_with_findings` x2, `step_complete` x1
- 344,716 of 4,063,723 plan tokens = 8.5%, spent for zero detection
