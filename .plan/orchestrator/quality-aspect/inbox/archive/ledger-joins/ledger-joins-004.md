envelope_version=1
sender_type=plan
sender_id=ledger-joins
epic=quality-aspect
kind=candidate-lesson
created=2026-09-20T07:29:20Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-09-20

# Remediated review-bot findings fixed in-run before the merge gate

## Observation

Plan ledger-joins (PR #1545, merged) remediated one or more actionable
review-bot findings in-run: the run's pr-comment findings with resolution
fixed are non-zero, which is the slipped-then-caught defect class
lessons-capture exists to record. The automatic-review step state plus the
remediated findings together raised signal_automated_review_count = 1.

## Signal context

- Source: dispatcher-forwarded signal_automated_review_count = 1
  (outstanding/non-done automatic-review state, or remediated
  pr-comment findings with resolution fixed)
- Candidate classification is deferred to the orchestrator-side pickup; the
  plan transmits this record unjudged as kind: candidate-lesson for the
  quality-aspect epic

## Provisional corrective direction (for orchestrator judgement)

Capture which review-bot rule fired, what the in-run fix changed, and whether
the finding class could have been caught earlier (outline, plan, or
per-deliverable verification) so the orchestrator can judge recurrence value
across plans.
