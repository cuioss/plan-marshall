envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:09Z

# Candidate lesson: S1130 triage accepted on a false premise about the pre-commit recipe

- Component: plan-marshall:phase-6-finalize
- Category: improvement
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-14-002 (created 2026-10-10), epic pm-mcp-core-m2-m4

- Component: plan-marshall:phase-6-finalize triage (Sonar java:S1130 on test methods); pm-mcp-parent recipe JUnit5BestPractices
- Signal: automated-review / Sonar round 2, fixed in TASK-19
- Evidence: decision log b06b23 (2026-10-10T09:10:13Z); TASK-019 "Sonar - unthrown exception on five test methods (S1130 x5)"

## What happened

In round 1 the triage accepted S1130 findings (1d700f, ae7998, 75e5c8) on the premise that the
`verify -Ppre-commit` recipe re-adds `throws` clauses, so removing them would be undone. That premise is false:
the recipe WIDENS an existing `throws` clause to `throws Exception` but never ADDS one (test methods without a
`throws` clause are stable at HEAD). Removal survives the recipe. Round 2 reversed the acceptance and fixed
all five in TASK-19, costing an extra loop-back.

## Suggested direction

Before accepting a Sonar finding because "the formatter will undo the fix", verify the claim against a file the
recipe actually left untouched; for S1130 in pm-mcp-core, remove the unthrown exception.

Source: inbox `lock-manager-and-leases-003.md`, plan lock-manager-and-leases (PLAN-01, #20).
