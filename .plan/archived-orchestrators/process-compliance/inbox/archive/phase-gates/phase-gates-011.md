envelope_version=1
sender_type=plan
sender_id=phase-gates
epic=process-compliance
kind=candidate-lesson
created=2026-09-19T14:27:48Z

title=Owed hint: suppress external-infra check failures with spend-cap evidence
component=plan-marshall:phase-6-finalize
category=improvement

Owed `architecture enrich` call (filed post-merge, do not run enrich here):

- target: --module plan-marshall
- verb: best-practice
- hint: "prefer to suppress [ci_policy_failure] findings in plan-marshall finalize runs because reviewer-backend outages (spend caps, rate limits) carry vendor evidence in the job log and no code fix exists — record the evidence, note the green-gate dependency, suppress"

Evidence: plan phase-gates suppressed 2 identical [ci_policy_failure] findings (eac137, 48d208) with Vertex AI 403 spend-cap evidence; recurrence 2/2 cleared preference_min_recurrence=2.
