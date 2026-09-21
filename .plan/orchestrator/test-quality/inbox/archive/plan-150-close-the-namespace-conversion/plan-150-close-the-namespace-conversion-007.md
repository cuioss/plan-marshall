envelope_version=1
sender_type=plan
sender_id=plan-150-close-the-namespace-conversion
epic=test-quality
kind=candidate-lesson
created=2026-09-02T21:54:37Z

component=plan-marshall:automatic-review
category=improvement
confidence=medium
source_plan=plan-150-close-the-namespace-conversion

# Weight in-house self-review over external bots in the finalize step budget

## Context

On PR #1383 the external review bots contributed zero findings. `automatic-review` settled
three bots and recorded "0 actionable comments"; the post-merge review-retrospective graded
`indeterminate` over its entire enabled roster because all three rows were unmeasurable.

Every defect caught during finalize came from an in-house gate. `pre-submission-self-review`
round 1 found 4 defects the bots did not, all fixed in commit `4f8b0733a`, and round 2
confirmed those classes closed. The plan's own conversion work additionally exposed two
production-relevant defects the bots also did not find: a lesson id
(`2026-04-15-099`) that `validate_lesson_id` rejects because the format is
`YYYY-MM-DD-HH-NNN`, and an unreachable stub branch matching `--task`/`task` where the CLI
declares `--task-number`/`task_number`.

Meanwhile the external path cost a `loop_back`, a rate-window stall (CodeRabbit reported 0
of 1 hourly included reviews remaining), and an operator-authorized barrier override.

## Root cause

The finalize budget treats external bot review as a gating quorum and in-house review as a
step among many. On this plan's evidence the value ran the other way: the gating path
produced nothing and cost a stall, while the non-gating path produced everything.

One run is not a calibration. But it is a data point worth recording precisely because the
gating asymmetry is structural rather than measured — nothing currently compares the two
paths' yield.

## Proposed action

Record per-plan review yield by source (in-house gate versus each external bot) so the
gating asymmetry can be re-evaluated against a corpus rather than an intuition. Then
reconsider whether an external bot belongs in `required_bots` when its measured yield over
that corpus is zero and its failure mode is a non-convergent stall.

## Evidence

- status.metadata.phase_steps — `automatic-review`: "3 bots settled, 0 actionable comments (coderabbit reviewed 4f8b073)", `prior_firings: [loop_back]`, `firing_count: 2`
- status.metadata.phase_steps — `project:finalize-step-review-retrospective`: "indeterminate - 0 findings and no reviewer produced content; comparison not performed"
- status.metadata.phase_steps — `pre-submission-self-review`: "self-review clean: 70 candidates examined, no check matched" on round 2, after round 1 found and fixed 4 defects
- status.metadata.merge_authorizations.barrier-ask-override — granted because "Re-firing cannot converge ... CodeRabbit reports 0 of 1 hourly included reviews remaining, so no fresh review is obtainable in the window"
