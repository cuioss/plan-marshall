envelope_version=1
sender_type=plan
sender_id=cross-repo-telemetry-archive-and-analyze
epic=post-run-quality
kind=candidate-lesson
created=2026-10-03T23:22:14Z

component=plan-marshall:phase-6-finalize
category=improvement

# Forward --step-id on every dispatch boundary and keep recording past the loop-back ceiling

## Context

All 33 dispatch-boundary rows in this plan (1 plan, 12 execute, 20 finalize) are keyless: no --step-id was forwarded, so the key-first join paired 0 of 33 boundary rows with the 41 execution-log rows. The 6-finalize boundary ledger also stops at 13:16:33Z. After the self-review ceiling breach and the operator override, nothing was recorded for any later dispatch: the final self-review round, four automatic-review dispatches (including the one stopped after ~1h), and the post-merge steps.

## Root cause

The finalize dispatcher calls record-dispatch-boundary without --step-id. After the loop-back ceiling is breached and an operator override resumes the phase in main context, the boundary recording is no longer driven by the normal per-step dispatch loop.

## Proposed action

Pass --step-id {step key} on every record-dispatch-boundary call (execute and finalize), and make the override / resume path re-enter the same per-dispatch recording, including stopped or abandoned dispatches (harness_cancellation).

## Evidence

- aspect: execution_context_dispatch_audit firing_comparison - keyless_boundary_rows 1 / 12 / 20, paired_firings 0 in every phase; channel_completeness confidence low (4 finalize dispatch lines vs 40 completions)
- aspect: logging_gap_analysis - finalize boundary rows end 13:16:33Z; work.log shows dispatches until 23:16Z
- aspect: routing_decisions cost_preview - 11 of 41 execution-log rows unmeasured
