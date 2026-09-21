envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=candidate-lesson
created=2026-09-04T16:33:46Z

component=plan-marshall:manage-tasks
category=improvement
confidence=medium
source_plan=every-module-counts-and-the-campaign-can-finish

# declared_set_closure rewards shrinking the declaration, which is the wrong end of the discrepancy

## Context

At 4-plan the `declared_set_closure` mechanical check fired twice:

- TASK-010 declared step target `test`, which deliverable 7 never declares
- TASK-011 declared step target `.claude`, which deliverable 8 never declares

Both are correct observations. Both were resolved by DELETING the step: the undeclared `test/` survey step was removed from TASK-010, and the undeclared `.claude` survey step was removed from TASK-011. In each case the reasoning recorded was that the outline's structured `survey_scope` did not carry the root — the whole-tree mention existed only in outline prose and was never parsed into the structured set.

The declaration and the task were reconciled. The reconciliation moved the task down to the declaration, not the declaration up to the work.

## Root cause

The check names one discrepancy and admits two repairs — "add the path to the deliverable" or "correct the step" — and the second is always cheaper. Deleting a step is one edit with no re-derivation; widening a deliverable means re-deriving its file set and re-validating the outline. Under a check that blocks, the cheap repair wins by default.

For a SWEEP that is precisely backwards. The `.claude/` root the TASK-011 step named is a root ruff actually lints, and the plan had just spent a Q-Gate round establishing that its residue was unknown and had to be swept. The step was right; the declaration was thin.

## Downstream consequence

The plan's realized footprint came to 521 paths against 221 declared-and-hit, and the retrospective reads the 300-path difference as scope creep. Part of that gap is the sweep-declaration form problem already filed separately as a candidate. This is the other part, and it is a distinct cause: a mechanical gate actively pushed two declarations narrower during 4-plan, and the paths it removed then shipped anyway.

## Proposed action

Make the repair direction explicit in the finding rather than symmetric. When the undeclared target belongs to a deliverable whose scope is predicate-shaped (a sweep), the default repair should be to widen the declaration, and narrowing should require a stated exclusion rationale — the same asymmetry the 3-outline `scope_criterion_validator` findings already apply ("add them, or record a per-file exclusion rationale so the residue is declared rather than silent").

The two checks currently pull in opposite directions on the same plan, one round apart.

## Evidence

- qgate findings dfc826 and ba7435 (4-plan, `plan-marshall:manage-tasks:qgate-mechanical-checks`, warning), both `taken_into_account` by removing the step
- qgate findings ba4603 and 4c7f43 (3-outline, `scope_criterion_validator`) — same run, opposite instruction: declare the residue or justify it
- The `.claude` root removed from TASK-011 at 4-plan is the same root the operator ruled at 3-outline could not be left unknown (finding 75c38e), and 3 files under it are in the shipped write-set
