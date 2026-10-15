envelope_version=1
sender_type=plan
sender_id=antigravity-execution-fidelity
epic=live-blockers
kind=candidate-lesson
created=2026-10-14T21:31:34Z

component=plan-marshall:manage-metrics
category=improvement
title=Record dispatch-boundary rows for 6-finalize dispatches

# Record dispatch-boundary rows for 6-finalize dispatches

## Context

The antigravity-execution-fidelity retrospective found no
`work/metrics-dispatch-boundaries-6-finalize.toon` on a plan that dispatched
heavily throughout finalize (16 terminal finalize steps, 72 DISPATCH lines).
The per-dispatch termination-cause audit therefore covered 4-plan and 5-execute
only, and the firing comparison graded 6-finalize as not_evaluated.

## Root cause

Finalize step dispatches never call `manage-metrics record-dispatch-boundary`,
so the boundary ledger has no finalize-side rows to pair against the 62
finalize execution_log rows.

## Proposed action

Have the finalize dispatcher call `record-dispatch-boundary --phase 6-finalize`
with the step key and termination cause on every dispatched finalize step
return, mirroring the phase-5-execute call sites.

## Evidence

- aspect: logging-gap-analysis — no metrics-dispatch-boundaries-6-finalize.toon; audit covers 4-plan plus 5-execute only
- aspect: execution-context-dispatch-audit — firing_comparison 6-finalize not_evaluated, 62 execution rows with no boundary side
- confidence: high; source plan: antigravity-execution-fidelity
