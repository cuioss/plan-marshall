envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T07:42:09Z

# Candidate lesson: a required review bot never re-reviews after fix pushes when the repo uses the merge queue

Source: script/process failure observed at finalize (automatic-review / branch-cleanup participation barrier), PR #25.

The required review bot `cuioss-review-bot` reviewed once and never re-reviewed after the fix commits were pushed. With `use_merge_queue=true` the branch is never rebased locally, so branch-cleanup's trigger A (re-review after rebase) never fires. The participation barrier therefore never cleared, and an operator override was needed to get past it.

Note: the repo-side change in #24 ("re-request the review bot after a fix commit") targets this same area, but it did not produce a re-review in this run.

Candidate rule / fix direction: the re-review trigger for required bots must also fire on a fix push when the merge queue is in use (no rebase), or the barrier must request the re-review explicitly. A required participant that cannot be re-triggered should not need a manual override.

Scope hint: plan-marshall framework (phase-6-finalize branch-cleanup / automatic-review), possibly also the cuioss-organization review-bot workflow.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-04-service-unit-007.md` from plan plan-04-service-unit (PLAN-04, #25)
