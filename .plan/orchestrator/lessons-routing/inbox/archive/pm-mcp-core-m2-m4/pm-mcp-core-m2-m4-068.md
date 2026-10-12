envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:09Z

# Candidate lesson: pre-push-quality-gate and executor drift probe degrade in a Maven consumer project

**Signal source**: orchestrator observation, verified in the plan work log (WARNING lines in 6-finalize).

**Component (suggested)**: `plan-marshall:phase-6-finalize` (pre-push-quality-gate, sync-baseline executor refresh)

## Evidence

- 2026-10-11T06:53:50Z: "Footprint paths matched a build_map glob but resolved to no bundle: 57 pm-workflow paths (derive_gate_bundles resolves marketplace bundles only; this is a Maven project)". The per-bundle arm gated nothing.
- 2026-10-11T06:57:45Z: "No module-tests canonical resolves in this project at default scope, so the module-tests divergence arm could not run its own invocation". The whole-tree `verify -Ppre-commit` (245 tests) was green, so the gate passed on honest degradation.
- 2026-10-11T06:52:51Z: sync-baseline "executor refresh: drift=unknown ... drift probe returned no usable verdict (consumer project, no marketplace/bundles)".
- Decision log 19:09:31Z: manifest compose kept pre-push-quality-gate "on an unknown build verdict: plan footprint unresolvable" because no worktree existed at 4-plan.

## Why it matters

In a consumer repository (no `marketplace/bundles`), two of the gate's arms and the drift probe cannot produce a verdict at all. Today this is logged as a warning on every finalize. The gate's assurance then rests on the whole-tree arm alone.

## Suggested direction (for orchestrator classification)

Map footprint paths to build-system modules (here Maven modules such as `pm-workflow`) in consumer projects, resolve a module-tests canonical from the architecture (`test -pl {module} -am`), and give the drift probe a consumer-project branch.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-004.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
