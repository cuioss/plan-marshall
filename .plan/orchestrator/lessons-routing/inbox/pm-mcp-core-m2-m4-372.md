envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:04Z

component=plan-marshall:phase-3-outline
category=anti-pattern

# Renaming or splitting states missed the specification parts that cite them

Source: Q-Gate 4-plan finding 760b6e (scope_criterion_validator under_coverage, deliverable 2; resolved in run), plan plan-70-plan-instance-alignment.

D2 made the plan unit call plan, execute and finalize once per lane, which renames or splits the call states (`phases.outline-rework`, `phases.execute-reentry`, the entry `rework`). Its affected files listed 8 spec parts; a content search over `doc/specification` for those names also hit state-catalogue 07 and 04, workflow-dsl 02 and 03 (and 07 for INV-INIT-2). None was in any deliverable. To avoid a third re-plan, the orchestrator carried the parts into TASK-1/TASK-2 as extra steps - which then surfaced as the 20-file scope-creep warning in 5-execute (finding 124472).

## Rule

When a deliverable renames, splits or removes a named state, anchor or call, the outline runs a content search for every old name over the whole specification tree and lists every hit, or states per hit that the name stays. Carrying the misses into tasks without updating the declared footprint trades a re-plan for a later scope-creep finding.
