envelope_version=1
sender_type=plan
sender_id=lb-26-execute-loop-triage
epic=live-blockers
kind=candidate-lesson
created=2026-10-14T11:06:26Z

title=Owed architecture hint: test-failure dispositions in plan-marshall
category=improvement
component=plan-marshall:phase-6-finalize

Owed `architecture enrich` call (filed by finalize-step-preference-emitter; do NOT apply before the plan archives):

- module: plan-marshall
- verb: insight
- hint: the project treats test-failure as a standing consideration in plan-marshall

Basis: 5 taken_into_account test-failure dispositions within plan lb-26-execute-loop-triage,
recurring on test pins owned by a pending rewrite (clearing preference_min_recurrence=2).
Reconstructible enrich call:
`python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture enrich insight --module plan-marshall --insight "the project treats test-failure as a standing consideration in plan-marshall"`
