envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-14T13:31:55Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan static-verifier-residuals (PLAN-56, pm-mcp-core #66, merged 7981d17), drained 2026-10-14.
> Source inbox message(s): static-verifier-residuals-005.md static-verifier-residuals-010.md 
> RECURRENCE of lessons-routing inbox messages already routed by this epic: pm-mcp-core-m2-m4-205, -216, -229, -237 (queued); -068, -104 (archived). Fold into those; this is new evidence from another plan, not a new lesson.

# Candidate lesson: pre-push gate degrades on a Maven multi-module project

Plan: static-verifier-residuals (PR plan-marshall/pm-mcp-core#66).
Signal source: orchestrator observation during 6-finalize (pre-push gate).

## What happened

- `derive_gate_bundles` resolved no bundles for this Maven multi-module project (pm-core,
  pm-workflow, pm-runtime, pm-providers/*), so the pre-push gate had no bundle set to run.
- The `test-compile` and `module-tests` canonical commands did not resolve at default scope
  (they are module-scoped in this repository: `test -pl {path} -am`).

The pre-push gate therefore degraded instead of running the module tests of the changed
modules; correctness rested on the separate full verify.

## Candidate rule

The pre-push gate should derive its scope from the realized footprint mapped to Maven modules
(architecture which-module on each changed path) and invoke the module-scoped canonicals per
affected module, falling back to the root `verify` canonical rather than degrading when no
bundle mapping exists. A degraded gate must name what it skipped so it is not read as green.

## Suggested owner

plan-marshall phase-6-finalize pre-push gate (derive_gate_bundles) and/or build-maven /
manage-architecture canonical resolution for multi-module projects. Classification deferred
to the orchestrator.

component=plan-marshall:phase-6-finalize
category=bug
title=Derive pre-push gate scope from Maven modules, not only marketplace bundles

# Derive pre-push gate scope from Maven modules, not only marketplace bundles

## Context

In static-verifier-residuals (a Maven multi-module repository), pre-push-quality-gate logged: "Footprint paths matched a build_map glob but resolved to no bundle: 26 pm-workflow source/test paths (derive_gate_bundles is marketplace-bundle-shaped; this Maven project has modules, not bundles)". The step completed as "0 bundles; whole-tree gate, coverage, ITs green; module-tests DEGRADED".

## Root cause

derive_gate_bundles maps the footprint to marketplace bundles only, so on a module-structured build system the per-module gate scope is empty and the step falls back to the whole-tree gates while reporting module-tests as degraded.

## Proposed action

Resolve the gate scope through the architecture module mapping (`architecture which-module`) when the build system is module-structured, so module-tests run on the touched modules (here pm-workflow) and are not reported degraded.

## Evidence

- aspect: log-analysis — work.log 12:27:53 [WARNING] (plan-marshall:pre-push-quality-gate) Footprint paths matched a build_map glob but resolved to no bundle
- status.metadata.phase_steps.6-finalize.pre-push-quality-gate.display_detail: "0 bundles; whole-tree gate, coverage, ITs green; module-tests DEGRADED"
