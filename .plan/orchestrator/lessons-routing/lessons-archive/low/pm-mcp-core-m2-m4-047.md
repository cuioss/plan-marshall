envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T07:42:12Z

# Candidate lesson: emit [DISPATCH] lines and step_id keys when finalize re-fires steps after a loop-back

Source: plan-retrospective of plan-04-service-unit (aspects execution-context-dispatch-audit, logging-gap-analysis). Not covered by the 10 lessons-capture messages.

## Context

Finalize ran three passes because of two loop-backs to 5-execute. On the re-entry passes, the re-fired `automatic-review` (first loop-back), `sonar-roundtrip` (both re-fires) and `wait-region-unified-triage` completed with no `[DISPATCH]` work-log line. The dispatch audit counted 7 finalize dispatch lines against 17 step completions (ratio 0.41, confidence low). In addition, all 9 dispatch-boundary rows (4-plan, 5-execute, 6-finalize) carry no `step_id`. firing_comparison therefore paired 0 of the 20 execution_log rows, and per-step dispatch spend cannot be attributed. The orchestrator also noted an ordering slip: unified-triage round 2 was admitted before its dispatch.

## Root cause

The re-entry path of phase-6-finalize re-fires steps without going through the logging seam that emits `[DISPATCH]` and the `Executing step` line. `record-dispatch-boundary` is called without the step key.

## Proposed action

- Route re-entry re-fires through the same dispatch helper as first fires, so `[DISPATCH]` and `[STEP] Executing step` are always written.
- Pass `step_id` (for example `automatic-review` or `verify:quality-gate`) to `record-dispatch-boundary` at every call site.
- Add a test that a loop-back re-fire produces a paired dispatch line and a keyed boundary row.

## Evidence

- execution-context-dispatch-audit: `channel_completeness.ratio 0.412, confidence low`; `firing_comparison` 6-finalize `paired_firings 0`, `keyless_boundary_rows 4`, `unpaired_execution 14`
- work.log lines 290, 333 (sonar-roundtrip Completed with no Executing/DISPATCH), 289-292 (automatic-review re-fire with no DISPATCH line), 297 (unified triage Complete with no DISPATCH)
- decision.log 20:46:18: "wait-region-unified-triage round 2 was admitted before its dispatch (orchestrator ordering slip)"

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-04-service-unit-013.md` from plan plan-04-service-unit (PLAN-04, #25)
