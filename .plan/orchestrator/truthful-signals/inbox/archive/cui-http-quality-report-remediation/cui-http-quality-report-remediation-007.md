envelope_version=1
sender_type=orchestrator
sender_id=cui-http-quality-report-remediation
epic=truthful-signals
kind=candidate-lesson
created=2026-10-05T07:59:06Z

component=plan-marshall:manage-metrics
category=bug

# Candidate lesson: execute-phase metrics possibly double-counted; execution_log missing later loop-back rounds

**Source signal**: metrics anomaly observed by the finalize orchestrator (reported by the dispatcher). Partially corroborated: the decision log records `verify:module-tests` / `verify:coverage` record-step rows for 5-execute both at 11:52-11:53Z and again at 13:29Z (loop-back round 2), and the finalize record-step rows stop being emitted per step after loop-back iteration 2.
**Component**: plan-marshall:manage-metrics and plan-marshall:manage-execution-manifest (record-step / execution_log).

## What happened

- Execute-phase metrics appear to accumulate across loop-back re-entries in a way that may count the same phase twice.
- The execution_log has no rows for the later finalize loop-back rounds (iterations 3-5), so the run's late cost is not attributed.

## Candidate rule

Loop-back re-entry into 5-execute / 6-finalize must append distinct per-round rows (keyed by loop_back_iteration) rather than re-adding to or silently skipping the phase totals.

## Classification hint

Marketplace defect candidate (plan-marshall bundle); needs confirmation against metrics.toon before filing.

## Routing

From cui-http epic `quality-report-remediation`, PLAN-10 (#256); previously lesson 2026-10-04-06-007. Routed by the cui-http orchestrator on 2026-10-05 (operator directive: all plan-marshall findings go to `truthful-signals`).
