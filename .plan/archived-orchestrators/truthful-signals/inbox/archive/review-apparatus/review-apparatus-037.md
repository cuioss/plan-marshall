envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-13T09:04:33Z

# Carry-forward cleanup: `_foreign_paths_by_deliverable` is a test-only shim after PR #1473

Transferred from epic `review-apparatus` (inbox `the-foreign-gate-population-and-branch-f-recovery-006.md`,
2026-09-13). ⭐ **Routed here at its sender's own request**: the sending plan stated outright that the
item is NOT `review-apparatus` charter — it is a `phase-6-finalize` code cleanup — and that it reached
that epic only because an archiving plan's inbox is its one route out. It fails the PR/review test, so
it lands here rather than being folded into a review-apparatus spec.

## The item

Finding `86f76a`, plan `the-foreign-gate-population-and-branch-f-recovery` (PR #1473, merged
`38af136ed`), resolution `taken_into_account` — correct on the merits, deliberately not acted on.

That plan's D1 rewrote `_foreign_paths_by_deliverable` into a pure delegation
(`return _partition_foreign_paths(deliverables).by_deliverable`) with **zero production callers** —
`check()` calls `_partition_foreign_paths` directly because it needs both tuple fields. The wrapper is
kept alive only by tests: five call sites in `test_foreign_pr_gate.py` and one in
`test/plan-marshall/manage-solution-outline/test_survey_scope_declaration.py`.

File: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py`

## Why it could not be done in the plan that created it

`test_survey_scope_declaration.py` was declared **read-only** in that plan's outline and had to pass
UNCHANGED as D1's behaviour-preservation proof. Two of the six call sites live there, so deleting the
wrapper in that branch would have falsified the success criterion the refactor rested on.

⭐ **That is the transferable part, and it generalises past this wrapper**: a refactor whose proof of
behaviour-preservation is *"these tests pass unchanged"* cannot also delete what those tests call. The
residue is created by the proof, not by carelessness, so it is predictable — and therefore worth
transferring rather than re-discovering.

## The follow-up

Self-contained and unconstrained now that D1 has landed: delete `_foreign_paths_by_deliverable` and
repoint the six test call sites at `_partition_foreign_paths(...).by_deliverable`.

⚠ **Lead, not instruction.** The call-site count (5 + 1) is the sending plan's, first-party to its own
run but not re-derived in this checkout at HEAD — re-derive it before acting, since #1473's own tests
moved that file.
