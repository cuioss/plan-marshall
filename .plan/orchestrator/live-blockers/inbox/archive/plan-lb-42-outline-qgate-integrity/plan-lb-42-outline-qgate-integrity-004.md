envelope_version=1
sender_type=plan
sender_id=plan-lb-42-outline-qgate-integrity
epic=live-blockers
kind=candidate-lesson
created=2026-10-15T11:47:44Z

component=plan-marshall:phase-5-execute
category=improvement
title=Reduce agent-initiated re-dispatch in 5-execute voluntary checkpoints
source_plan=plan-lb-42-outline-qgate-integrity
confidence=medium

# Reduce agent-initiated re-dispatch in 5-execute voluntary checkpoints

## Context

The plan-lb-42-outline-qgate-integrity retrospective counted 8 voluntary_checkpoint terminations out of 14 5-execute dispatches (57%), crossing the 50% agent-initiated re-dispatch threshold, while all 6 remaining dispatches exited clean with an empty queue.

## Root cause

Dispatch envelopes yield on voluntary checkpoints instead of driving the pending queue to clean_exit_queue_empty inside a single envelope, so each checkpoint pays a fresh dispatch setup for work the same envelope could have continued.

## Proposed action

Have the execute-task loop continue past progress checkpoints while tasks remain pending, reserving voluntary_checkpoint yields for genuine budget exhaustion or blocking input.

## Evidence

- aspect: logging_gap_analysis — DISPATCH_TERMINATION_CAUSE 8 of 14 voluntary_checkpoint in 5-execute (57%)
- aspect: log-analysis — dispatch_boundaries 5-execute rows corroborate the same distribution
