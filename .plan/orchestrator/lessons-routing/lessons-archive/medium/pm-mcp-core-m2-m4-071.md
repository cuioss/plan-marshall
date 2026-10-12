envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:11Z

# Candidate lesson: spec self-contradictions surfaced only during execute and needed operator decisions mid-execute

**Signal source**: orchestrator observation, verified in the plan decision and work logs.

**Component (suggested)**: `plan-marshall:phase-2-refine` (source premise verification) / epic spec authoring (`plan-orchestrator` re-grounding)

## Evidence

- Refine 2026-10-10T18:00:38Z: "Source premise verification: 6 claims checked, 6 valid, 0 invalid". Neither contradiction below was caught.
- Decision log 2026-10-10T21:55:25Z (mid-execute, envelope 4): "Operator decisions mid-execute: instance header follows the PlanInstanceHeader store schema (code fix TASK-9 ...; AST spec listing corrected in TASK-8 step A); unit question.adjudicate renamed to adjudicate.decisions in the spec". This added TASK-009 "Align the instance header with the PlanInstanceHeader store schema".
- Decision log 2026-10-11T06:32:35Z (at execute exit, after the move to 6-finalize): "rename adjudication primitives question.check-adjudication/vote-roles/decide-agreement to adjudicate.* now". 5-execute was re-opened and TASK-010 "Rename the adjudication primitives off the reserved word question" was added.

## Why it matters

Two contradictions between specification documents (AST instance header vs the store schema; the reserved word `question` used in unit and primitive ids) were found only when the code was written. Each one cost an operator interruption and a re-opened phase. Refine's premise check verifies claims against the source, but not specification documents against each other.

## Suggested direction (for orchestrator classification)

Before a plan launches, run a cross-spec consistency pass in refine or in the epic's spec re-grounding: compare the AST listing with the store schema, and check identifiers against the grammar's reserved words. When a plan spec cites several specification documents, check them for shared terms that contradict each other.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-007.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
