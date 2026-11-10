envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-11-07T14:28:23Z

component=plan-marshall:phase-6-finalize
category=bug
source_plan=pm-mcp-core:plan-v2-98-optional-conversion-workflow

# Honour loop-back close --waive-refire in the pre-merge HEAD binding

## Context

In 6-finalize of pm-mcp-core PLAN-V2-98 the operator closed a loop-back with `loop-back close --waive-refire`, waiving the re-fire of code-review at the new HEAD. The pre-merge barrier then refused with `merge_candidate_not_gated`, because its HEAD binding requires a code-review completion at the merge HEAD and does not read the waiver. The waived code-review had to be re-run before the queue merge (code-review firing_count 8).

## Root cause

The waiver is recorded by the loop-back close but the pre-merge `merge_candidate_not_gated` check binds each gated step to `head_at_completion` only and has no path that accepts an operator waiver for that HEAD.

## Proposed action

Make the pre-merge HEAD binding read the waiver record (step, HEAD, operator basis) and accept a waived step at that HEAD, reporting it as waived rather than gated. Add a test: waive-refire then pre-merge at the same HEAD must pass without a re-fire.

## Evidence

- aspect: chat-history-analysis - re-run of the waived code-review before merge
- aspect: plan-efficiency - 6-finalize 1.92M tokens (floor), code-review fired 8 times
- operator report at finalize
