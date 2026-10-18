envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:16:43Z

# Candidate lesson: Do not mark a write-replace step done when its file did not change

Source: plan-retrospective (request-result-alignment + functional-review false self-report), plan-69-unit-frontmatter-and-types
Component (suggested): plan-marshall:execute-task (foreign bundle - route to plan-marshall lessons inbox)
Category (suggested): bug

## Context

TASK-15 (deliverable 9, a survey deliverable) carried six `write-replace` steps for specification files that were to be re-pointed. During execution the agent decided to keep the three grammar anchors as pointer sections, so those six files needed no change and stayed untouched (decision db547c). TASK-15 nevertheless finalized steps 7-12 as done. The functional review graded this a false self-report in three rounds; the outline and the request-result comparison still count the six files as expected mutations, so D9 reads 2 of 8.

## Root cause

Step finalization accepts `done` for a `write-replace` step without checking that the step's target appears in the task's diff, and there is no "verified, no change needed" outcome that records a decision to leave a declared file alone.

## Proposed action

When finalizing a `write-replace` step, compare its target against the task's changed files; if unchanged, require an explicit outcome such as `skipped` / `no_change_needed` with a reason (or a decision-log reference) instead of `done`, so the self-report, the outline and the realized footprint agree.

## Evidence

- functional review (rounds 1-3): "TASK-15 still marks those write-replace steps done, which I listed as a false self-report"
- artifact-consistency: 6 outline_only paths = exactly the six untouched D9 spec files
- envelope 5 return: "Because the anchors stay, I left the references in the six spec files of task 15 untouched"
