envelope_version=1
sender_type=plan
sender_id=plan-footprint-is-unknowable-to-its-own-graders
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T14:44:54Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=medium
source_plan=plan-footprint-is-unknowable-to-its-own-graders
source_pr=1359

# Finalize returns to the operator once per step-group despite a standing continue-to-end instruction

## Context

Of the 10 operator-authored turns in this session, **six** are instructions to continue finalize to completion, in six different wordings:

- "continue with finalize until completed" (×4)
- "do continue until end of finalize"
- "continue with finalize to the end"
- "conitune with finalize withotu further stoppoing" (two typos — the sixth restatement)

Plus one bare "retry". The wording drift and the typos are the signal: the operator was re-issuing an instruction they had already given, not supplying new information.

## Root cause

The finalize FOR loop returns control to the main context between step groups. An operator instruction to "continue to the end" is consumed by one continuation and not retained across the next return, so each return costs one operator round-trip.

## Proposed action

Persist a continue-to-end intent for the finalize phase (a `status.metadata` flag set when the operator says so) and consult it at each continuation point, so the loop resumes without a prompt until it hits a genuine gate — a loop-back ceiling, a merge authorization, or an unresolved finding.

Note the boundary: gates that genuinely need an operator decision (this run had four, including two that expanded the spec) must still stop. The target is the returns that ask nothing.

## Evidence

- aspect: chat_history_analysis — `operator_turn_count: 10`, of which 6 are continue-instructions and 1 is a bare retry; `gate_decision_count: 4`.
- Finalize spend on this plan was 4,450,750 dispatched tokens across 824 tool uses — 51 % of the whole plan's dispatched total and the largest single phase, so the per-return cost lands on the most expensive phase.
- 20 dispatch-boundary rows in 6-finalize (15 `step_complete`, 5 `returned_with_findings`) against 6 operator re-issues.
- Confidence is medium: the count is unambiguous, but no measurement isolates how much spend the returns themselves cost.
