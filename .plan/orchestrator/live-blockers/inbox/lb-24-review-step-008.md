envelope_version=1
sender_type=plan
sender_id=lb-24-review-step
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T11:58:37Z

component=plan-marshall:phase-6-finalize
category=improvement

# Self-review review-fix commits after an operator override of the round cap

## Context

In plan lb-24-review-step the pre-push self-review used all five fix rounds. Each fix was right on its target but introduced one or two new blocking gaps in the finalize instructions it rewrote (wake-delay budget, failed-commit loop-back, false timeout prompt, held replies). At the ceiling the operator chose "Fix it, then close by your decision", and the step was then closed by operator override again at heads 8fc4ed521 and c6571e103. The CodeRabbit review-fix commits (TASK-23, TASK-24, TASK-25) therefore shipped without any self-review, and CodeRabbit's second round found a real defect in TASK-24's fix-stamp recovery, which the operator then reversed ("Require evidence for both"). About 4.9M dispatched tokens went into the five self-review rounds.

## Root cause

The override closes the step for every later head, not only for the head the operator judged; the step has no narrower mode that reviews just the delta a fix commit introduced once the round budget is spent.

## Proposed action

After an operator override, keep a delta-only self-review for later fix commits (scoped to the files the fix commit changed, no round budget charge) instead of carrying the override forward; record which heads were closed by override so the review-retrospective can say what shipped unreviewed.

## Evidence

- status: pre-submission-self-review firing_count 9, six loop_back firings, facts may_close=operator_override
- decision.log 2026-10-09T18:39:55Z: loop-back ceiling reached; 19:40:29Z operator decision
- decision.log 2026-10-10T06:47:34Z and 08:40:12Z: closed again by operator override at 8fc4ed521 and c6571e103
- review-retrospective: later review-fix commits were never self-reviewed
