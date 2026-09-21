envelope_version=1
sender_type=plan
sender_id=plan-01-script-surface-validation
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-11T19:21:59Z

# Candidate lesson — Argparse rejection cluster on paraphrased manage-* verbs and flags
key=value envelope:
component=plan-marshall:tools-script-executor
category=anti-pattern
title=Argparse rejection cluster on paraphrased manage-* verbs and flags
plan_id=plan-01-script-surface-validation

4 distinct failing notations across [FAILED], script_failure, voluntary_checkpoint markers (7 occurrences): manage-logging work (2), manage-tasks add and pack-envelopes --per-envelope-budget-tokens 400K (2), automatic-review review_completeness check (1), manage-status mark-step-done (1), plus phase_handshake verify script_internal_error main_checkout_dirtied (1). Every argparse case traces to paraphrased verbs or invented flags versus the canonical invocation. Check the canonical-forms table and --help before new manage-* calls; route values as flag args, never inline env or shell assembly.
