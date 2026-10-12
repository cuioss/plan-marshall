envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:10Z

# Candidate lesson: execution manifest step-param snapshot goes stale against live marshal.json during a plan

**Signal source**: orchestrator observation, verified in the plan decision log.

**Component (suggested)**: `plan-marshall:manage-execution-manifest`, `plan-marshall:automatic-review`

## Evidence

- Decision log 2026-10-11T07:55:09Z: "Mailbox advisory pm-mcp-core-m2-m4-001 verified and applied: plan-local automatic-review re_review_on_loopback false -> true (live marshal.json carries true since #24; manifest snapshot predates it)".
- The manifest was composed at 4-plan (2026-10-10T19:09). Upstream #24, which changed `.plan/marshal.json`, had landed before that on main but after plan creation. The worktree absorbed it later, but the manifest kept the old step-param value.
- Only the orchestrator inbox advisory caught the drift, before the first finalize loop-back re-review.

## Why it matters

Step params frozen into the manifest silently override a project config change made during the plan. Here that would have skipped the bot re-review after a loop-back fix commit.

## Suggested direction (for orchestrator classification)

Re-resolve step params from live marshal.json at step execution time (as `step_execution_tier` already does: "leaf re-resolves live at execute time"), or detect snapshot drift at finalize entry and refresh it with a logged decision.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-006.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
