envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=finding
created=2026-10-12T12:40:46Z

# [HIGH][Antigravity] The cross-repository documentation deliverable was skipped without a trace

- Component: plan-marshall:phase-3-outline (cross-repository deliverables), plan-marshall:phase-6-finalize (foreign-PR gate), traced-implementation flow
- Category: bug

## What happened

- The spec's standing constraint says that requirement and specification documents, and the deletion of implemented specification sections and watch items, are made in `plan-marshall-documentation` by the plan.
- PLAN-41 implemented Workflow DSL watch items PM-WATCH-DSL-3/4/5/8/9/11/15/16/29/32, but no PR was opened in `plan-marshall-documentation`, neither its #35–#39 nor any branch.
- The landing message does not mention it, and the foreign-PR archive gate did not object.
- Every earlier plan of the epic under Claude Code opened that PR.

## Why it matters

The watch items stay open on documentation main although the code implements them, and nothing in the landing tells the orchestrator. That last point is the real defect: the deliverable vanished silently.

## Suggested direction

- The outline always materializes the documentation deliverable when the trace matrix touches watch or specification items.
- The foreign-PR gate fails closed when that deliverable exists in the outline but no foreign PR was recorded.

- Priority: **HIGH** (operator decision 2026-10-12: Antigravity issues are filed directly as high priority)
- Platform: Antigravity — first plan of epic pm-mcp-core-m2-m4 run under it
- Plan: `plan-41-static-verifier-remaining-rules` (PLAN-41), pm-mcp-core PR #34, merge commit ebe82b3
- Evidence location: pm-mcp-core `.plan/local/archived-plans/2026-10-12-plan-41-static-verifier-remaining-rules/` (logs/, metrics.md, execution.toon, build-results/)
- Origin: filed by the orchestrator of epic pm-mcp-core-m2-m4 from its landing analysis, verified against the archived plan and the PR
