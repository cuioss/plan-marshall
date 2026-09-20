envelope_version=1
sender_type=plan
sender_id=finalize-step-contract-guard-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T10:22:55Z

component=plan-marshall:phase-5-execute
category=bug
confidence=high
source_plan=finalize-step-contract-guard-residue

# Record dispatch boundaries in 5-execute so its terminations are audited by something

## Context

The plan directory holds `work/metrics-dispatch-boundaries-4-plan.toon` (1 row) and `work/metrics-dispatch-boundaries-6-finalize.toon` (10 rows). There is no `-5-execute.toon`.

`5-execute` unquestionably dispatched: `analyze-logs` inferred 3 dispatch clusters from the work log (1 starting marker, 2 re-entering markers), and 15 tasks reached `done` in that phase for 1,210,592 dispatched tokens.

The `DISPATCH_TERMINATION_CAUSE` rule in `logging-gap-analysis.md` is precondition-guarded on the file's existence — "Plans without the artifact skip the rule entirely." The guard exists so the rule does not false-positive on plans predating the artifact. Its effect here is that the plan's **implementing** phase, the second-largest token consumer, has its dispatch terminations audited by nothing, and the audit reports no finding about it.

The same absence propagates: `4-plan` is separately marked `PARTIAL: 1 of 4 dispatch(es) recorded`, so even the phase that does emit rows emits them for a quarter of its dispatches.

## Root cause

Two compounding causes. First, `phase-5-execute` does not call `record-dispatch-boundary` at its dispatch terminations the way `phase-6-finalize` does. Second, the consuming rule's precondition cannot distinguish "this plan predates the artifact" from "this phase should have written the artifact and did not" — a file-existence guard fails toward silence for both.

## Proposed action

Call `manage-metrics record-dispatch-boundary --phase 5-execute` at every execute-dispatch termination, matching the finalize dispatcher's existing behaviour.

Independently, tighten the consuming rule so absence is legible: when a phase has dispatch evidence from another channel — inferred dispatch clusters in the work log, or a non-zero `subagent_samples` from enrich — but no boundary file, emit a `missing_boundary_file` finding rather than skipping. The retrospective already computes the corroborating evidence, so the discriminator is available at no extra cost. This mirrors the `missing_dispatch_emission` treatment `check-dispatch-audit` already applies: an instrumentation finding against the recorder, not a discipline finding against the phase.

## Evidence

- artifact manifest: `work/metrics-dispatch-boundaries-{4-plan,6-finalize}.toon` present; no `-5-execute` file
- aspect: log_analysis — `phase5_logging_gaps.dispatch_clustering.inferred_dispatches: 3`
- aspect: log_analysis — `4-plan` boundary total marked `PARTIAL: 1 of 4 dispatch(es) recorded`
- reference: `logging-gap-analysis.md` DISPATCH_TERMINATION_CAUSE — "Plans without the artifact skip the rule entirely"
