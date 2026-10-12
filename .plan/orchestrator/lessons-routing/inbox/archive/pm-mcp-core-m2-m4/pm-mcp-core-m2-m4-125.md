envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=finding
created=2026-10-12T12:40:44Z

# [HIGH][Antigravity] Phase boundaries not closed: 4-plan has no end, 5-execute has no start, and the execute phase left no task or dispatch trail

- Component: plan-marshall:manage-status (phase boundaries), plan-marshall:phase-4-plan, plan-marshall:phase-5-execute, plan-marshall:plan-marshall orchestrator loop
- Category: bug

## What happened

- `metrics.md`: "Phases missing an end_time boundary marker — 4-plan". 4-plan starts at 06:39:09Z with no end; 5-execute has no start and ends at 08:39:39Z. Landing facts carry `step.record-metrics.any_phase_missing_end_time=true`.
- The decision log has 44 lines and **no entry at all between 06:52:03Z (4-plan Q-Gate) and 08:34:23Z** (verify:quality-gate recorded). The work log shows execute starting with "8 tasks pending", and then nothing per task. Zero dispatch-boundary rows in the decision log, two `DISPATCH` mentions in the work log.
- Yet 1,200+ lines of `WorkflowValidator` and four feature commits landed between 07:12Z and 07:39Z, i.e. Rules 1–12 in 27 minutes.

## Why it matters

The plan lifecycle's audit trail is the operator's and the orchestrator's only way to verify what execute did. Here it is empty, so the orchestrator had to reconstruct execute from git history alone. A plan that bypasses the per-task flow can skip the per-task verification steps unseen.

## Suggested direction

- Make the phase transition refuse to advance when the previous phase has no end marker.
- Detect "execute produced commits but recorded no task completion" and fail closed or warn loudly at finalize.
- Check whether Antigravity runs the execute leaves at all, or whether the main agent implements inline.

- Priority: **HIGH** (operator decision 2026-10-12: Antigravity issues are filed directly as high priority)
- Platform: Antigravity — first plan of epic pm-mcp-core-m2-m4 run under it
- Plan: `plan-41-static-verifier-remaining-rules` (PLAN-41), pm-mcp-core PR #34, merge commit ebe82b3
- Evidence location: pm-mcp-core `.plan/local/archived-plans/2026-10-12-plan-41-static-verifier-remaining-rules/` (logs/, metrics.md, execution.toon, build-results/)
- Origin: filed by the orchestrator of epic pm-mcp-core-m2-m4 from its landing analysis, verified against the archived plan and the PR
