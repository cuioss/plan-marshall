envelope_version=1
sender_type=plan
sender_id=the-foreign-gate-population-and-branch-f-recovery
epic=review-apparatus
kind=candidate-lesson
created=2026-09-13T08:20:27Z

component=plan-marshall:phase-6-finalize
category=improvement

# Carry-forward cleanup: _foreign_paths_by_deliverable is a test-only shim after PR #1473

**Routing note first.** This item is NOT `review-apparatus` charter — it is a
`phase-6-finalize` code cleanup. It is transmitted here only because this epic's inbox is
the one route out of the archiving plan, and a finding named but never transferred dies with
the plan directory. Re-route it wherever the orchestrator keeps non-charter carry-forward.

## The item

Finding `86f76a` from plan `the-foreign-gate-population-and-branch-f-recovery`, resolution
`taken_into_account` (correct on the merits, deliberately not acted on).

Deliverable D1 rewrote `_foreign_paths_by_deliverable` into a pure delegation
(`return _partition_foreign_paths(deliverables).by_deliverable`) with ZERO production
callers — `check()` calls `_partition_foreign_paths` directly because it needs both tuple
fields. The wrapper is kept alive only by tests: five call sites in
`test_foreign_pr_gate.py` and one in
`test/plan-marshall/manage-solution-outline/test_survey_scope_declaration.py`.

## Why it could not be done in that plan

`test_survey_scope_declaration.py` was declared read-only in the plan's outline and had to
pass UNCHANGED as D1's behaviour-preservation proof. Two of the six call sites live there,
so deleting the wrapper in that branch would have falsified the success criterion the
refactor rested on.

## The follow-up

Self-contained and unconstrained now that D1 has landed: delete
`_foreign_paths_by_deliverable` and repoint the six test call sites at
`_partition_foreign_paths(...).by_deliverable`.

File: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py`
