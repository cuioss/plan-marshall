envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:16Z

## Candidate lesson: foreign-PR archive gate assumes the plan branch name in the foreign repository

Component: plan-marshall:phase-6-finalize (scripts/foreign_pr_gate.py)
Category: bug

The pre-archive foreign-PR landing gate classifies every foreign repository on the plan's own branch name,
`feature/{plan_id}`. A plan whose outline puts the foreign change on a different branch (here
deliverable 5 used `docs/workflow-dsl-parser-and-ast` in plan-marshall-documentation, by outline
decision) makes the gate fail closed with `foreign_landing_indeterminate` ("Could not resolve the tip
SHA of branch 'feature/workflow-dsl-parser-and-ast'"), even though the foreign PR
(plan-marshall/plan-marshall-documentation#27) was merged as 9f220c0.

Effect: the only ways past are a fabricated branch (gaming the gate) or an operator-authorised direct
archive; this run used the latter, recorded in the plan's decision log.

Suggested direction: let the gate take the foreign branch (or the foreign PR number) from the
deliverable / references rather than assuming `feature/{plan_id}`, or have the outline/phase-4 refuse a
foreign deliverable whose branch name the gate cannot classify.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-020.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
