envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:50Z

# A foreign-repository deliverable has no finalize step that pushes it and opens its PR

## Observation

Deliverable 11 (the documentation pull request in plan-marshall-documentation) was implemented as local commits (7a3fd8b, 8ce51ab, a8d4db9) on that repository's feature branch. Finalize's push / create-pr / ci-verify / branch-cleanup steps operate only on the plan's own repository, so the documentation branch was handed back as a free-text "to do by the orchestrator" note and nothing in the plan record shows it was pushed or opened before the code PR merged and the plan moved to retrospective. The retrospective cannot confirm deliverable 11 shipped.

## Suggested direction

- Record foreign-repository deliverables structurally (repo path, branch, commits) when phase 5 completes them, and add a finalize step (or extend push/create-pr) that pushes each and opens its PR, or at minimum gates the pre-merge confirmation on an explicit operator acknowledgement that the foreign PR is outstanding.
- Include the foreign PR URL/state in the landing message so the epic orchestrator sees it.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `runtime-lifecycle-023.md` from plan runtime-lifecycle (PLAN-08, #29)
