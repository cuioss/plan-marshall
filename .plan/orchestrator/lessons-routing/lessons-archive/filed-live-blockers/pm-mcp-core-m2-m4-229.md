envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T13:50:28Z

# Candidate lesson: derive_gate_bundles selects nothing in a Maven repository

- Source: dispatcher observation (in-run, not a filed finding)
- Plan: session-log-and-generations (PR #51)

## Observation

`derive_gate_bundles` resolves marketplace bundles only. In this Maven repository
(pm-mcp-core, no `marketplace/bundles/` tree), the per-module quality-gate step
therefore selects nothing. The `test-compile` and `module-tests` canonicals it would
dispatch do not exist for this project either. The per-module gate is silently empty
rather than mapped to the Maven modules the plan touched.

## Possible lesson

For a non-marketplace project, gate-bundle derivation should map the plan's footprint
to build-system modules (here the Maven modules from the architecture inventory). It
should use only canonicals the project's build domain declares. Failing that, it should
report explicitly that the per-module arm selected zero modules and why, so an empty
gate is not taken for a passing one. Candidate owner: plan-marshall:phase-5-execute or
plan-marshall:phase-6-finalize (gate derivation), with plan-marshall:build-maven for the
canonical set.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `session-log-and-generations-006.md` from plan session-log-and-generations (PLAN-12, #51; Claude Code)
