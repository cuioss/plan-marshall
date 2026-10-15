envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T18:29:12Z

# Resolve module-tests canonical for Maven before reporting the gate degraded

## Context

On its first firing (work.log 12:41:22, df9056), pre-push-quality-gate logged "No module-tests canonical resolves in this project, so no pytest could be run and the divergence question cannot be answered — the scoped-green / whole-tree-red divergence class (PLAN-08) is UN-GATED". It finished as "module-tests gate DEGRADED" on all 8 firings. The project is a Maven multi-module build. Its execution manifest carries `verify:module-tests` (tier per_task) in phase_5.verification_steps, and the project CLAUDE.md lists per-module test commands (`test -pl {path} -am`) for pm-core, pm-workflow, pm-runtime and the five provider modules.

## Root cause

The divergence check seems to resolve its module-tests canonical along a pytest-shaped path (the message names pytest). For a Maven project it finds nothing, even though the same canonical resolves for phase-5 verification. The gate therefore degrades on every push of every Maven plan, and the PLAN-08 divergence class goes unchecked without anyone noticing.

## Proposed action

Resolve the module-tests canonical through the same architecture seam that phase-5 `verify:module-tests` uses, for every build system. Word the degradation message without naming pytest. If the degradation persists for a build system, report it once per project (for example in marshall-steward health) rather than as a per-plan warning.

## Evidence

- log-analysis: work.log WARNING df9056 (pre-push-quality-gate) as quoted above
- manifest-decisions: phase_5.verification_steps includes verify:module-tests, step_execution_tier per_task
- status.json phase_steps 6-finalize pre-push-quality-gate display_detail "module-tests gate DEGRADED", firing_count 8

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-39-module-readmes-and-adrs-009.md` from plan plan-39-module-readmes-and-adrs (PLAN-39, #53; Claude Code)
