envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:04Z

component=plan-marshall:phase-5-execute
category=improvement

# Scope-creep warning fired on files the plan had knowingly added outside the declared footprint

Source: Q-Gate 5-execute finding 124472 (scope_creep_check, 20 files outside declared scope, threshold 5; resolved in run as accepted), plan plan-70-plan-instance-alignment.

All 20 files were known and reviewed: spec parts added by Q-Gate finding 760b6e and carried into tasks by the orchestrator, stale change-type wording checks, and two operator decisions taken during execute (empty-list grammar with ADR workflow-dsl/006; settled pruned gate with ADR workflow-plan/016). None were defects, but the declared footprint was never updated, so the check could not tell them from real creep and needed an operator acceptance.

## Rule

When a Q-Gate finding or an operator decision adds files to the work after outline (carried into tasks instead of a re-plan), record them in the declared footprint at that moment, so the 5-execute scope-creep check measures real drift instead of re-reporting accepted decisions.
