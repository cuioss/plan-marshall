envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-13T09:16:44Z

component=plan-marshall:platform-runtime
category=bug
bundle=plan-marshall

# Exclude harness-injected subagent hand-backs from the chat extract-signal operator count

## Context

Observed in PLAN-V2-40 (plan-v2-40-envelope-packing, PR #402) by the plan retrospective's chat-history aspect. `chat extract-signal` reported `operator_turn_count: 32` for session 8d2d88a2. Of those 32 kept turns, 29 are harness messages of the form "Another Claude session sent a message: <agent-message ...> [Subagent hand-back]" — subagent reports that the harness itself labels as model output carrying no user authority. Only three turns were typed by the operator ("continue unattended...", "continue", and "continue" after `/login`).

## Root cause

The operator-provenance predicate of the reduction keys on the `user` role of the transcript record, and the harness delivers subagent hand-backs in user-role turns. The predicate does not recognise the hand-back frame, so subagent output is counted and kept as operator signal.

## Proposed action

Classify a user-role turn that carries the `<agent-message from=...>` hand-back frame (or the harness's "Another Claude session sent a message" wrapper) as a harness injection, not an operator turn: count it under `residual_counts` (or a separate `subagent_handback` counter) and keep it out of `operator_turn_count`. `no_signal` then reflects genuine operator input, and the chat-history aspect no longer reads subagent reports as user pivots. Cover it with a fixture transcript holding one hand-back and one operator turn.

## Evidence

- aspect: chat-history-analysis — extract-signal output operator_turn_count 32, gate_decision_count 0, kept 32 of 1557 raw turns; 29 of the 32 are agent-message hand-backs
- aspect: permission-prompt-analysis — evaluated over the same 32 kept turns
