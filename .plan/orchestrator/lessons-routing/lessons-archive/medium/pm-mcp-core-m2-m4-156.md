envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T06:54:49Z

# Candidate lesson: leaf phase skills transition the phase themselves

- Component: plan-marshall:phase-3-outline, plan-marshall:phase-4-plan, plan-marshall:phase-5-execute (with plan-marshall:plan-marshall as the orchestrator)
- Suggested category: bug
- Signal: orchestrator observation, corroborated by the logs

## Observation

Dispatched phase leaves moved the plan to the next phase on their own. 3-outline moved to 4-plan
while it was returning an outline prompt to the operator, so the orchestrator had to re-open
3-outline. 4-plan moved to 5-execute and 5-execute moved to 6-finalize, so the orchestrator skipped
its own transition.

## Evidence

- decision.log 2026-10-12T15:46:50Z (plan-marshall:planning): "phase-3-outline self-transitioned to
  4-plan while returning an outline_prompt; re-opened 3-outline for the single permitted re-dispatch."
- work.log 2026-10-12T16:18:28Z (plan-marshall:plan-marshall): "4-plan already transitioned by
  phase-4-plan leaf - orchestrator transition skipped".
- work.log 2026-10-12T18:36:24Z (plan-marshall:phase-5-execute): "transitioning 5-execute -> 6-finalize."

## Suggested correction

Make one party own phase transitions. Either the leaves never transition and return a signal, or
the leaves own it and the orchestrator contract says so. A leaf returning a prompt-required envelope
must never transition.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-engine-004.md` from plan workflow-engine (PLAN-13, #45; Claude Code)
