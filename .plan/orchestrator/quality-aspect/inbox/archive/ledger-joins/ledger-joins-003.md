envelope_version=1
sender_type=plan
sender_id=ledger-joins
epic=quality-aspect
kind=candidate-lesson
created=2026-09-20T07:29:18Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-09-20

# Resolved Q-Gate verifier_unavailable findings closed without verifier rerun

## Observation

Plan ledger-joins (PR #1545, merged) closed 3 Q-Gate findings of class
verifier_unavailable as resolved-in-run. The verifier that would normally
re-check the finding was unavailable, so the resolution was recorded on the
strength of the run's own evidence rather than a verifier rerun.

## Signal context

- Source: dispatcher-forwarded signal_qgate_pending_count = 3
- Scope: findings across 2-refine, 3-outline, 4-plan, 5-execute, 6-finalize,
  pending and resolved-in-run alike
- Candidate classification is deferred to the orchestrator-side pickup; the
  plan transmits this record unjudged as kind: candidate-lesson for the
  quality-aspect epic

## Provisional corrective direction (for orchestrator judgement)

When a verifier is unavailable, record exactly what substitute evidence the
resolution rested on (which run output, which reviewer sign-off) so a later
verifier pass or audit can re-check the finding without re-deriving context.
