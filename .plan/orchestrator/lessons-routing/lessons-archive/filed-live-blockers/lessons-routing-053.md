# The manifest composes verification steps the project cannot run, and the tier decision hands sweeps back mid-run

Severity: high. Bundle: **plan-marshall** (`manage-execution-manifest`, `manage-architecture` resolve / tier decision, `phase-5-execute`). Filed under RULING 2026-10-09 (a).

Recurrence: four plans, every one of them.

## Sources

- corpus `2026-10-11-06-003`, `2026-10-11-16-005`
- inbox `pm-mcp-core-m2-m4-312`, `-328`, `-386`

## Consolidated statement

1. **Unresolvable composed steps.** The manifest emits `phase_5.verification_steps = [verify:quality-gate, verify:module-tests]` without checking that each canonical resolves for the plan's scope. In a Maven reactor repository `module-tests` does not resolve at the root ("only verify exists"), so a leaf ran `verify -pl pm-core -am` and recorded it under an invented step id (`verify:module-tests:pm-core`); the steps the manifest names are never recorded, and the dispatch audit shows 4-5 unpaired `verify:*` rows per plan. The exit sweep then had to argue the owed step away because the whole-tree verify covers it.
2. **Tier oscillation and hand-backs.** A plan-time `bash_timeout_seconds` snapshot (370 s) drove an in-leaf decision, the run was killed at 341 s, and a fresh resolve then reported ~777 s and orchestrator tier; another run resolved `per_task` (567 s) after three orchestrator-tier hand-backs. One slow run flips the tier and the next estimate flips it back, with nothing damping the oscillation. All three `voluntary_checkpoint` boundaries in one plan were whole-tree sweeps (`verify -Ppre-commit`, execute-exit `verify -pl … -am`) started on a `per_task` bound; the orchestrator re-attached each time. Elsewhere 4 of 7 and 4 of 10 dispatches ended `voluntary_checkpoint` for the same reason.

## What is asked

- At compose time, resolve each candidate verification step against the architecture; drop or replace (e.g. by `verify`) a step that does not resolve, and log the substitution as a decision. Define the per-module record key the manifest expects.
- Classify the end-of-execute whole-tree quality gate and the execute-exit verify as `execution_tier: orchestrator` when the recorded duration of the same canonical command exceeds the leaf bound (or always for whole-tree sweeps), so it runs once with the correct timeout instead of handing back a running job.
- Apply hysteresis within a plan: once orchestrator-tier, stay there until several runs come in well under the ceiling; or separate a timeout from a tier signal so a single killed run raises the budget without forcing a hand-back.
- Before running any verification whose duration could exceed the leaf ceiling, re-resolve it live and treat the task's stamped value as advisory; report the tier history in the build verdict.
- Let execute consult the build-freshness ledger to auto-record a pending verify step already covered by an orchestrator run on the same tree.

## Evidence

As recorded by the senders. Not re-verified against HEAD in this run.
