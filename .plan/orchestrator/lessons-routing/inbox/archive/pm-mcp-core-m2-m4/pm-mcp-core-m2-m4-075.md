envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:12Z

# Candidate lesson: a sanctioned yield for orchestrator-tier verification was reclassified as a no-progress error

**Signal source**: `voluntary_checkpoint -> error` reclassification (one of the three script-failure marker classes) in 5-execute.

**Component (suggested)**: `plan-marshall:phase-5-execute` (dispatch-boundary no-progress classifier)

## Evidence

- Decision log 2026-10-10T20:46:20Z: "(plan-marshall:phase-5-execute:no-progress) reclassified voluntary_checkpoint as error — in_progress=1, completed_delta=0, tokens=290713 (yield_reason=orchestrator_tier_verification; TASK-3 steps 1-10 implemented; orchestrator runs quality-gate + verify for pm-workflow then re-dispatches envelope 2)".
- Work log 20:45:35Z: the leaf stated it had finished TASK-3 steps 1-10 with compile green, and left step 11 open until the orchestrator-tier gate passed. The orchestrator ran the builds (20:46-20:47) and the next envelope completed TASK-003 at 20:49:53Z.

## Why it matters

`yield_reason=orchestrator_tier_verification` is the documented hand-off for a build the leaf must not run itself. The classifier measures progress only by completed tasks, so a task that is legitimately held open for the orchestrator's verification counts as "no progress" and is logged as an error. This inflates the script-failure signal and could trip no-progress limits on large tasks.

## Suggested direction (for orchestrator classification)

Count completed steps (not only completed tasks) toward progress, or exempt `yield_reason=orchestrator_tier_verification` from the no-progress reclassification when steps advanced in the envelope.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-012.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
