envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:47Z

# Orchestrator stops after a budget_yield envelope return instead of dispatching the next envelope

## Observation

Phase 5 ran in four plan-time-packed envelopes. After envelope 1 and again after envelope 2 returned `budget_yield: true` with a `next_envelope_id`, the main-context orchestrator ended its turn without dispatching the next envelope. The operator had to type "did you stop?" both times to get execution moving. Envelope 3's return was followed by the next dispatch without a nudge, so the stall is intermittent, not structural to every yield.

A `budget_yield` return is a deterministic continue signal: the bin-packer already decided the grouping, tasks remain, and no operator decision is pending.

## Suggested direction

- In the phase-5 envelope loop, treat `budget_yield: true` + `next_envelope_id` as an unconditional re-dispatch, and say so as a hard rule in the orchestrator workflow (no turn end between envelopes).
- Add a retrospective check that flags an operator turn between a `budget_yield` boundary row and the next envelope's `[STATUS] Re-entering` line, so recurrences are counted.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `runtime-lifecycle-018.md` from plan runtime-lifecycle (PLAN-08, #29)
