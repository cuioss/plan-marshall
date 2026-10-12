envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:08Z

# Candidate lesson: dispatched phase leaves self-transition the plan although the orchestrator owns the transition

**Signal source**: orchestrator observation, verified in the plan work and decision logs.

**Component (suggested)**: `plan-marshall:phase-3-outline`, `plan-marshall:phase-5-execute`, `plan-marshall:plan-marshall` (orchestrator boundary handling)

## Evidence

- Decision log 2026-10-10T18:43:01Z: "re-opened 3-outline (leaf had self-transitioned to 4-plan)". The orchestrator had to `set-phase 4-plan -> 3-outline` twice (18:43:00Z and 18:54:18Z) to run its outline review gate and fold operator answers.
- Work log 2026-10-10T22:23:36Z: phase-5-execute leaf logged "transitioning 5-execute -> 6-finalize" itself.
- Work log 2026-10-10T22:28:14Z: "Resume reconciliation: stamped missing metrics boundary 5-execute -> 6-finalize (leaf self-transitioned)". The metrics boundary was left half-stamped.
- 2026-10-11T06:31:59Z: orchestrator set the phase back 6-finalize -> 5-execute to add TASK-10 after an operator decision.

## Why it matters

The orchestrator's post-phase review gate and extra work (operator review of the outline, required builds on the final tree) run AFTER the leaf returns. A leaf that advances the phase forces the orchestrator to set it back, which writes loop-back markers that look like real loop-backs, and leaves metrics boundaries inconsistent.

## Suggested direction (for orchestrator classification)

Either the phase leaves return a "ready to transition" signal and the orchestrator performs the transition (and stamps the metrics boundary) after its gate, or the contract states explicitly that the leaf transitions and the orchestrator's gate runs before dispatch return is accepted, with the metrics boundary stamped in the same call.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-002.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
