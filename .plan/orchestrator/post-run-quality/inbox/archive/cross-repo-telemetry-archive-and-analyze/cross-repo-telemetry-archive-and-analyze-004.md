envelope_version=1
sender_type=plan
sender_id=cross-repo-telemetry-archive-and-analyze
epic=post-run-quality
kind=candidate-lesson
created=2026-10-03T23:21:44Z

component=plan-marshall:plan-marshall
category=bug

# Record execute-phase operator escalations as blocked_user_review, not error

## Context

Four of the twelve 5-execute dispatch-boundary rows carry termination_cause=error (07:17Z, 09:50Z, 10:54Z, 11:40Z). Each one was an orchestrated hand-back to the operator, not a failure: TASK-1 escalate_ask (no sanctioned GitHub repo-create path), TASK-9 blocked on test-failure triage (missing target trees), envelope 5 escalate_ask (roster-row timing), TASK-16 blocked (Glob not granted). All four were resolved by an operator answer and the plan continued. The ledger therefore reports error_total_tokens=1,285,813 as genuinely wasted spend.

## Root cause

The orchestrator's after-dispatch classification maps escalate_ask and status: blocked returns to the error cause, although DISPATCH_TERMINATION_CAUSES already carries blocked_user_review for exactly this outcome.

## Proposed action

In the plan-marshall execution workflow's "After execution-context returns" classification, map escalate_ask / prompt-required / blocked-on-operator returns to blocked_user_review, and keep error for genuine terminal failures only.

## Evidence

- aspect: log_analysis dispatch_boundaries 5-execute - 4 error rows, error_total_tokens=1285813
- aspect: logging_gap_analysis - the 4 error rows match the 4 operator escalations one-for-one
- aspect: chat_history_analysis - each escalation followed by an operator-decision turn and a successful re-dispatch
