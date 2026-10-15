envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T17:39:56Z

# Candidate lesson: pre-push-quality-gate is permanently DEGRADED in a Maven (non-marketplace) project

**Source plan:** plan-21-entity-addressing
**Signal source:** orchestrator-observed event; the DEGRADED module-tests arm is verified in decision.log (bcb3a3: "module-tests arm DEGRADED as before (no default-scope module-tests canonical)"); the "derive_gate_bundles returns 0 bundles" detail is the orchestrator's observation and was not found verbatim in the plan logs
**Suggested component:** plan-marshall:phase-6-finalize (pre-push-quality-gate standard / workflow)

## What happened

- In pm-mcp-core (a Maven multi-module project, no marketplace bundles), the pre-push-quality-gate assumes marketplace bundles: derive_gate_bundles yields 0 bundles, and there is no default-scope module-tests canonical command (module tests run only per module with `test -pl {path} -am`).
- The gate therefore reports DEGRADED on every firing (three firings this run), even though the orchestrator ran the full whole-tree verify -Ppre-commit, verify -Pcoverage and integration tests green at the same HEAD.

## Gap

A gate that is DEGRADED by construction in a whole class of projects carries no signal and trains operators to ignore it. The standard has no path for a build-system project without bundles or without a default-scope module-tests canonical.

## Possible corrective action

Let the pre-push-quality-gate fall back to the project's architecture-resolved canonical commands when no bundles are derived (e.g. whole-tree `verify` or the quality-gate canonical as the module-tests arm), or treat "no default-scope module-tests canonical" as a configured not-applicable arm rather than DEGRADED.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-21-entity-addressing-004.md` from plan plan-21-entity-addressing (PLAN-21, #54; Claude Code)
