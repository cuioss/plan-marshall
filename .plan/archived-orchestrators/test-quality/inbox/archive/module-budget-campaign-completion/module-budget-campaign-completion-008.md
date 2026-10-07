envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=test-quality
kind=candidate-lesson
created=2026-09-23T14:49:49Z

component: plan-marshall:phase-6-finalize
category: improvement
status: active

# Owed architecture hint: preference-emitter, plan module-budget-campaign-completion

One pattern cleared the within-plan recurrence threshold (2):

1. Target `--module plan-marshall`, enrich verb `insight`, hint text:
   "A ci-verify wait-budget lapse against still-running checks is taken into
   account (no failure verdict exists) and re-checked on retry rather than
   read as a red gate."

Reconstructible enrich call:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich insight --module plan-marshall --insight "A ci-verify wait-budget lapse against still-running checks is taken into account (no failure verdict exists) and re-checked on retry rather than read as a red gate."
```

Source pattern: (plan-marshall:phase-6-finalize, ci_timeout, accepted) x3
within this plan (findings a420b6, 0bac2e, 5dc82e — verify/CodeRabbit
still in progress at the precondition deadline, CI green at same HEAD on
re-poll). Third observation of the standing corpus pattern (see lessons
2026-09-21-11-001 and 2026-09-21-09-004); no new lesson allocated, owed hint
only.
