envelope_version=1
sender_type=plan
sender_id=build-path-evidence
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-12T00:54:34Z

title: Owed architecture hint - ci_timeout taken_into_account recurrence
module: plan-marshall:phase-6-finalize
enrich_verb: best-practice
hint: Treat a verify/verify CI timeout with the check still IN_PROGRESS as transient infrastructure noise (taken_into_account), not as a code defect; re-poll the check before filing a fix task.
pattern: (plan-marshall:phase-6-finalize, [ci_timeout] verify, taken_into_account) x2 meets preference_min_recurrence=2
plan: build-path-evidence
epic: tooling-truthfulness
