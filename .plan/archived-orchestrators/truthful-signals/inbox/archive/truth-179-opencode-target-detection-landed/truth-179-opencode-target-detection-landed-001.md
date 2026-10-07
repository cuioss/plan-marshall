envelope_version=1
sender_type=plan
sender_id=truth-179-opencode-target-detection-landed
epic=truthful-signals
kind=candidate-lesson
created=2026-09-25T13:22:03Z

# Fix manage-status transition internal error (7 hits this plan)

## Context

During plan truth-179-opencode-target-detection-landed the manage-status
transition subcommand raised a script-internal error (exit 1) 7 times, first
at 2026-09-24T16:54:23Z. The plan recovered and landed via PR #1619, so the
failures were retried or routed around rather than fixed.

## Root cause

Unknown. The transition path fails internally under conditions this plan hit
repeatedly; the stderr excerpt recorded no message, so triage starts from the
script log around the first timestamp.

## Proposed action

Reproduce the transition sequence from logs/script-execution.log around
2026-09-24T16:54:23Z and fix the internal error in the transition handler.

## Evidence

- aspect: script_failure_analysis — 7 occurrences of script_internal_error in plan-marshall:manage-status:manage-status transition, exit_code 1
- plan: truth-179-opencode-target-detection-landed (orchestrated, epic truthful-signals)

component: plan-marshall:manage-status
category: bug
confidence: medium
