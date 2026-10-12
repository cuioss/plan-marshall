envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:35Z

# Count only operator-authored turns in chat extract-signal, not subagent hand-backs

Component: plan-marshall:platform-runtime (chat extract-signal) via plan-marshall:plan-retrospective:extract-chat-signal
Category (proposed): bug
Confidence: high
Source: plan code-analysis-base, post-run-review retrospective (aspect chat-history-analysis)

## Context

The retrospective's chat pre-pass over session 1387a8b6 reported `operator_turn_count: 26` and `no_signal: false`. Of the 26 kept turns, 19 are subagent hand-back reports. The harness delivers them as user-role turns that start with "Another Claude session sent a message: <agent-message ...>". Only the launch command and the 6 recovered gate decisions came from the operator.

## Root cause

The operator-provenance predicate treats every user-role turn with free text as operator-authored. It does not recognise the harness frame for a subagent hand-back (`<agent-message from=...>` / "[Subagent hand-back]").

## Proposed action

Classify user-role turns that carry the agent-message hand-back frame as a separate population (for example `subagent_handback_count`), exclude them from `operator_turn_count`, and base `no_signal` on operator turns plus gate decisions only. Add a fixture transcript that mixes the two kinds of turn.

## Evidence

- aspect: chat-history-analysis: 26 kept turns; 19 begin with "Another Claude session sent a message"; 6 gate decisions; 1 command turn
- In an orchestrated plan, a session of hand-backs alone would pass as rich operator signal, which hides a quiet session from the Tier-2 skip logic

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `code-analysis-base-011.md` from plan code-analysis-base (PLAN-36, #31)
