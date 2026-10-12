envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:48Z

# chat extract-signal counts subagent hand-back frames as operator-authored turns

## Observation

The platform-runtime `chat extract-signal` reduction classifies every harness-delivered subagent hand-back (`user:` role, body starting "Another Claude session sent a message: <agent-message from=...>") as an operator turn. On this plan it reported `operator_turn_count: 25` where the operator actually typed 3 lines. The harness text itself says the frame "was not typed by your user".

Consequences: `no_signal` can never be true on an orchestrated session (every dispatch return counts as operator signal), and the reduced transcript is dominated by leaf reports rather than operator corrections, which is what the chat-history aspect is meant to surface (pivots, nudges, clarifications).

## Suggested direction

- Exclude the `<agent-message>` / "[Subagent hand-back]" frame from the operator-provenance predicate; count it under its own residual bucket (e.g. `subagent_handback`).
- Keep the frames available as a separate, optionally included stream so the retrospective can still read leaf reports when budget allows.
- Add a fixture test with a hand-back frame asserting it does not raise `operator_turn_count`.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `runtime-lifecycle-019.md` from plan runtime-lifecycle (PLAN-08, #29)
