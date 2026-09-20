envelope_version=1
sender_type=plan
sender_id=the-foreign-gate-population-and-branch-f-recovery
epic=review-apparatus
kind=candidate-lesson
created=2026-09-13T08:28:34Z

component=plan-marshall:automatic-review
category=insight
title=Review-pipeline detector defects found mid-finalize are carried forward, not fixed in the landing PR

## Owed architecture hint

- **Target `--module`**: `plan-marshall`
- **Enrich verb**: `insight` (`architecture enrich insight --module plan-marshall --insight "..."`)
- **Generalized hint text** (verbatim):

  > The project tolerates a review-pipeline detector defect discovered mid-finalize being carried forward to its owning epic rather than fixed in the landing PR. When the fix would advance HEAD and restart the mandatory re-review cycle, the containment cost outweighs the defect, so `accepted` — with the mechanism, the live observation, and a remedy direction recorded on the finding — is the preferred disposition rather than an in-PR fix.

## Why this is a preference, not an incident

The recurrence cleared the per-plan threshold (`preference_min_recurrence: 2`): the
same finding class — a detector/predicate defect in the automated-review pipeline,
observed live during this plan's own finalize — received the same `accepted`
disposition twice, each time with the same stated reason. That is a standing
project judgement about where such a fix belongs, not a one-off triage call.

The disposition is attributed to a concrete module (`plan-marshall`, via component
`plan-marshall:automatic-review`), so it clears the attribution gate and is
promotable.

## Filing note

This record is the discover-after-merge carrier for an owed `architecture enrich`
call. `default:finalize-step-preference-emitter` is `mutates_source: false` and
`post_run_review: true`, so it must not write `enriched.json` itself — that write
would land tracked source on `main` as an uncommitted diff after the merge gate.
The orchestrator performs the enrich (or routes it into a plan that can), using
the three facts named above.
