envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T06:32:46Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan plan-09-audit-trail (PLAN-09, pm-mcp-core #69, merged 3236ed5), drained 2026-10-15.
> Source inbox message(s): plan-09-audit-trail-012.md
> RECURRENCE of -214, -259 (quality-gate rewrite attributed as scope creep). Earlier numbers are lessons-routing messages pm-mcp-core-m2-m4-NNN.

# Pre-commit rewrite of untouched files tripped scope-creep (114 files)

- Source: Q-Gate record db52ba (5-execute, warning, scope_creep_warning), resolution `accepted` by operator.
- Suggested component: `plan-marshall:phase-5-execute` (scope_creep_check) / project-local quality gate.

## Observation

`verify -Ppre-commit` on pm-runtime rewrote the import layout of 117 files the plan never touched; TASK-8's envelope committed them separately (fa58482) and the scope-creep check then flagged 114 out-of-scope files. The operator chose to keep the rewrite in this PR.

## Candidate rule

Either the scope-creep check should recognise a commit produced purely by the quality-gate rewrite (and report it as such rather than as creep), or a plan that runs the pre-commit profile on a module with pending rewrites should land that rewrite first as its own change. Worth recording which so the next plan does not re-litigate it.
