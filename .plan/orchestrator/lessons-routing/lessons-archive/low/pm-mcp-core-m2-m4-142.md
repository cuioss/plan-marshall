envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T13:52:05Z

# Finalize dispatch-boundary rows stopped after round 5 and carry no step_id

Component (suggested): plan-marshall:phase-6-finalize (record-dispatch-boundary call sites) / plan-marshall:manage-metrics, category improvement (marketplace-owned)
Signal: plan-retrospective, log-analysis, logging-gap-analysis and execution-context-dispatch-audit aspects

## Observation

`work/metrics-dispatch-boundaries-6-finalize.toon` holds 9 rows, the last at 2026-10-12T06:01Z, while finalize kept dispatching review, CI and Sonar steps until the merge at about 12:59Z (29 execution_log rows, firing_count 10 on several steps). None of the 24 boundary rows across 4-plan, 5-execute and 6-finalize carries a `step_id`, so `firing_comparison` paired 0 of 44 execution rows. Three 5-execute rows record 0 tokens, 0 tool uses and 0 ms for dispatches that ran. The dispatch audit graded its channel confidence `low` (4 finalize dispatch lines against 44 completions), and the 6-finalize token row (7.2M, 55% of the plan) is a floor.

## Candidate directive

Forward `--step-id` on every `record-dispatch-boundary` call and record a boundary row for every finalize re-dispatch in later loop-back rounds; omit the token flags (unmeasured) rather than passing zeros when the return carried no usage.

Source: plan plan-11-enrolment-store (PLAN-11, PR #30); work/metrics-dispatch-boundaries-*.toon, execution.toon.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-11-enrolment-store-016.md` from plan plan-11-enrolment-store (PLAN-11, #30; Claude Code)
