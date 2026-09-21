envelope_version=1
sender_type=plan
sender_id=exit-code-convention-stops-at-the-skill-boundary
epic=review-apparatus
kind=candidate-lesson
created=2026-09-06T19:29:52Z

# An under-recorded declared footprint silently shrinks the lessons-consult population

component: plan-marshall:phase-3-outline
category: bug
confidence: high
source_plan: exit-code-convention-stops-at-the-skill-boundary
source_pr: 1423, 1429

## Context

This plan's lessons consult ran and reported success: `surfaced_count: 2`,
`total_matched: 2`, `truncated: false`. It scoped its search to
`components[1]: plan-marshall:tools-integration-ci` — a component set derived
from the plan's declared footprint of **9 files**. The realized footprint was
**158 files**, including **18 under `phase-6-finalize/`**.

Lesson `2026-08-27-16-005` (component `plan-marshall:phase-6-finalize`, from the
immediately preceding plan `a-failing-ci-call-reports-success`, PR #1356) records
that restating *this exact exit-code paragraph* in N documents produced two
multi-site defects at two consecutive HEADs, and its **Proposed action** is
verbatim what this plan eventually shipped:

> State the exit-code convention **once** — a single standards section — and
> replace the ten copies with an xref to it.

It was never surfaced, because `plan-marshall:phase-6-finalize` was not in the
consult's component set.

The plan therefore planned and executed D2 as **131 verbatim insertions** across
134 files (+1602/-10). The operator halted finalize at the review gate and
redirected to the single-source design, which the lesson had already prescribed.
Net effect flipped from +1602 lines to a removal of ~549. TASK-005 and TASK-006
re-ran execute for roughly two hours to undo it.

## Root cause

The lessons consult derives its component set from the **declared** footprint, and
the declared footprint is an under-recorded input (already filed as `5a7fff`,
9 vs 159). A consult scoped by that input searches a proportionally shrunken
corpus and reports a confident `surfaced_count` over it, with no field naming the
population it did not search. Under-recording the declaration is therefore not
merely a metrics nuisance — it **suppresses a capability**, and the suppression is
invisible at the consult site.

This is the same shape as the recall defect filed alongside it: a signal whose
apparent quality *improves* as the declaration shrinks.

## Proposed action

1. Widen the consult's component set beyond the declared footprint — at minimum,
   union in the components of the plan's *touched* surface as it becomes known,
   and re-run the consult at the phase-4/phase-5 boundary rather than once at
   outline.
2. Make the consult publish the population it searched: the component set, its
   size, and the corpus size it did **not** reach. A bare `surfaced_count: 2`
   cannot be told apart from "there were only 2".
3. Treat a lesson whose `Proposed action` contradicts a deliverable's declared
   shape as a blocking outline finding, not an informational one.

## Evidence

- `work/lessons-consult.toon` — `components[1]: plan-marshall:tools-integration-ci`,
  `surfaced_count: 2`, `truncated: false`
- `manage-lessons get --lesson-id 2026-08-27-16-005` — `component: plan-marshall:phase-6-finalize`
- `work/footprint.txt` — 158 realized paths, 18 under `phase-6-finalize/`
- `check-artifact-consistency` — `affected_files_recall declared=9 found=7 pass`
- `work.log` 13:32:36 `Phase: 6-finalize -> 5-execute`; 13:46:53 `Re-entering execute phase — 2 tasks pending`
- Related, already filed: `5a7fff` (the under-recording itself). This lesson is its
  downstream consequence, not a restatement.
