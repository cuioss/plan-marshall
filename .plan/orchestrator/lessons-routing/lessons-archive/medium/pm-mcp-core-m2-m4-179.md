envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:15Z

# Candidate (Q-Gate 4-plan, fixed): shared wiring file declared by one deliverable but edited by several (deliverable 4)

Source: Q-Gate finding f2f247, phase 4-plan, scope_criterion_validator under_coverage for deliverable 4; resolution fixed.

## Finding

Deliverable 4's success criterion requires ArgumentCheck to be called by VerifyNotResolvePipeline after stage 2. TASK-7 step 6 writes `VerifyNotResolvePipeline.java` (wiring stage 3), but deliverable 4's affected files left it out because only deliverable 2 declared it. declared_set_closure reported the same gap.

## Resolution

VerifyNotResolvePipeline.java (write-replace, stage 3 wiring) was added to deliverable 4's affected files and change-per-file.

## Lesson shape

This is the same pattern as 8143e0 (deliverable 3) and recurs within one plan. The outline author should declare a shared composition-root file in every deliverable that wires into it.

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-014.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
