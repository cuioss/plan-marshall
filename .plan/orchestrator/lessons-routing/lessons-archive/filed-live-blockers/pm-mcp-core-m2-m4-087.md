envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:32Z

# Candidate lesson: manage-tasks commit-add rejects deliverable 0 that the triage workflow prescribes for review-fix tasks

Component: plan-marshall:manage-tasks / plan-marshall:phase-6-finalize (triage workflow)
Category (proposed): bug
Source: plan code-analysis-base, review-fix rounds (script-failure cluster)

## Observation

The triage workflow prescribes deliverable `0` for review-fix tasks (fix tasks not owned by an outline deliverable). `manage-tasks commit-add` rejected deliverable `0` for those tasks, so the documented path fails at the script boundary and the fix commit had to be recorded another way.

## Proposed correction

Make the two agree: either `commit-add` accepts `0` as the "no deliverable / review-fix" sentinel, or the triage workflow names the deliverable the fix belongs to. Add a test that runs the exact invocation the triage workflow documents.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `code-analysis-base-005.md` from plan code-analysis-base (PLAN-36, #31)
