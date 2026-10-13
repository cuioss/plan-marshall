envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:15Z

# Candidate (Q-Gate 4-plan, fixed): shared wiring file declared by one deliverable but edited by several (deliverable 3)

Source: Q-Gate finding 8143e0, phase 4-plan, scope_criterion_validator under_coverage for deliverable 3; resolution fixed.

## Finding

TASK-5 step 4 writes `pm-runtime/src/main/java/de/planmarshall/runtime/job/VerifyNotResolvePipeline.java` (wiring stage 2). Deliverable 3's affected files left it out, because only deliverable 2 declared it. declared_set_closure reported the same gap.

## Resolution

VerifyNotResolvePipeline.java (write-replace, stage 2 wiring) was added to deliverable 3's affected files and change-per-file.

## Lesson shape

A pipeline or composition-root file that every stage-deliverable wires into must be declared in each deliverable that edits it, not only in the one that creates it. See the twin finding f2f247 for deliverable 4. The outline should list the file in every wiring deliverable from the start.

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-013.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
