envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T11:06:07Z

# Stop counting subagent hand-backs as operator turns in chat extract-signal

Component: plan-marshall:platform-runtime (category: bug, confidence: high)

## Context

For session 2437af47 (scenario-replay-harness), `extract-chat-signal` reported `operator_turn_count: 19` and
`kept_raw_count: 19`. Of those kept `user:` turns, 18 begin with "Another Claude session sent a message" and carry a
`[Subagent hand-back]` frame: they are subagent reports, not operator text. The real operator signal was the one
command invocation plus the 8 recovered gate decisions.

## Root cause

The operator-provenance predicate in `chat extract-signal` keys on the `user` role and does not recognise the
harness's agent-message hand-back frame, so agent output is counted as operator-authored.

## Proposed action

Recognise the `<agent-message ...>` / "Another Claude session sent a message" frame and count such turns separately
(e.g. `agent_handback_count`), excluded from `operator_turn_count`. Otherwise `no_signal` can never be true for an
orchestrated session and pivot detection reads agent reports as operator pivots.

## Evidence

- aspect: chat_history_analysis — operator_turn_count 19, gate_decision_count 8, 18 kept turns are hand-backs

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `scenario-replay-harness-012.md` from plan scenario-replay-harness (PLAN-22, #50; Claude Code)
