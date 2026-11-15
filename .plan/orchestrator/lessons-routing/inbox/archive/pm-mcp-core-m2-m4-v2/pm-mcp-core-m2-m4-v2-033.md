envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-13T18:20:20Z

component=plan-marshall:platform-runtime
category=bug
route=plan-marshall lessons-routing (foreign component, forward per standing rule)
confidence=high

# Exclude subagent hand-backs from the chat operator-turn count

## Context

For PLAN-V2-138 (pm-mcp-core, session 8e69e094) `chat extract-signal` returned `operator_turn_count: 71`, `kept_raw_count: 71`, `gate_decision_count: 1`. Reading the reduced transcript, about six of those turns are operator-authored (the /plan-marshall command, "continue unattended", two "continue", two "retry"); the rest are subagent hand-back reports that the harness delivers as user-role messages framed "Another Claude session sent a message: <agent-message ...> [Subagent hand-back]". Several hand-backs also appear twice (once plain, once after a tools-used-before-summary reminder).

## Root cause

The operator-provenance predicate of the chat extract-signal reduction treats every user-role turn that is not an empty or harness-injection turn as operator-authored, so harness-framed subagent hand-backs count as operator signal and the reduction keeps duplicates.

## Proposed action

In the platform-runtime chat extract-signal op, classify user-role turns carrying the agent-message hand-back frame as a separate residual class (for example `subagent_handback`), exclude them from `operator_turn_count`, and drop the exact duplicate of a hand-back already kept. Report the hand-back count beside the operator count so the chat-history aspect can still read them as context.

## Evidence

- aspect: chat_history_analysis - 71 operator turns vs about 6 operator messages; duplicated hand-backs from agents a7459ba4, a81c7f47, a74b552a, acf4ccee
