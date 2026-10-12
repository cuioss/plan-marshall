envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:48Z

# Disabled build server logs a WARNING on every build

## Observation

With the build server deliberately disabled for this project (`reason=disabled`), every build resolution writes a WARNING line to the plan work log. Across 64 maven builds this produced most of the plan's 70 work-log warnings, so a real warning (for example the module-tests DEGRADED notice) sits in a wall of identical expected-configuration lines.

## Suggested direction

- Log the `reason=disabled` resolution at INFO (or once per plan/session), and keep WARNING for genuine fallbacks (daemon down, registry mismatch, preflight failure).
- Retrospective log analysis can then treat a non-zero work-log WARNING count as a signal again.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `runtime-lifecycle-020.md` from plan runtime-lifecycle (PLAN-08, #29)
