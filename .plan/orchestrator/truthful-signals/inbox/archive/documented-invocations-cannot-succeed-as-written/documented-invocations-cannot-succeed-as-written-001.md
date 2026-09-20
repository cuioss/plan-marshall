envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T18:49:38Z

component=plan-marshall:phase-5-execute
category=bug
confidence=high
source_plan=documented-invocations-cannot-succeed-as-written
source_pr=1386

# Phase-5 yielded at orchestrator tier with its declared verification never run

## Context

The composed execution manifest declared three `phase_5.verification_steps` —
`verify:quality-gate` (per_task), `verify:module-tests` (orchestrator) and
`verify:coverage` (orchestrator). Phase-5 yielded at orchestrator tier and the
decision log records deliverable 3's tests as unrun at that point. The
end-of-phase verification sweep never executed.

The gap was closed only by accident of an unrelated event: the phase-6 to
phase-5 loop-back (7 pr-comment findings from `automatic-review`, triage opening
fix tasks) later re-fired the finalize settle band, and `pre-push-quality-gate`
reached `firing_count: 3` against the new HEAD `49769bd2f`. A plan that had not
looped back would have shipped with its declared end-of-phase verification unrun.

## Root cause

The phase-5 yield path has no gate asserting that the manifest's declared
`verification_steps` were executed before control returns. Nothing reports the
omission either: `manage-metrics reconcile-ledgers` shows `execution_log_rows: 0`
for `5-execute`, so not one `record-step` row exists for the phase at all, and
the absence is indistinguishable from a phase that declared no steps.

## Proposed action

Gate the phase-5 orchestrator-tier yield on the manifest's declared
`verification_steps` having a terminal record each, and emit a distinguishable
`verification_unrun` signal when the yield happens without them. The check has
both inputs already: the manifest lists the declared steps and the execution log
is where their records would land.

## Evidence

- aspect: manifest_decisions — `phase_5.verification_steps[3]` declared,
  `step_execution_tier`: `verify:module-tests=orchestrator`,
  `verify:coverage=orchestrator`
- aspect: logging_gap_analysis — `reconcile-ledgers` reports
  `5-execute: execution_log_rows: 0, boundary_rows: 6`, with all six rows
  classified `row_absent_from_execution_log`
- aspect: plan_efficiency — `pre-push-quality-gate` carries
  `firing_count: 3` with `prior_firings: [done, done]`, the re-fire that
  incidentally closed the gap
