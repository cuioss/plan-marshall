envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:05:39Z

# Candidate lesson: a comment claimed a population was derived while the tuple was hand-maintained

- source_signal: automatic-review / CodeRabbit inline (PR #1488)
- record_id: 4b2cfd (comment PRRC_kwDOQ3xasM7uheED)
- file: test/plan-marshall/phase-6-finalize/test_finalize_module_tests_divergence.py:748
- resolution: fixed via TASK-022 — derived from the gate document's Branch A non-run list

## What happened

`_MODULE_TESTS_DEGRADATION_TOKENS` was manually maintained despite the comment stating it is derived from the gate document. If the gate adds a degradation variant with a new spelling, the payload builder excludes it — and because the existing variants keep `payloads` non-empty, the green-claim sweep PASSES without ever checking the new variant.

## Candidate rule

The comment-versus-code divergence is the sharper half: a hand-maintained population under a comment that claims derivation defeats review, because the reviewer reads the claim and stops. Either derive it, or relabel the tuple a FLOOR and back it with an assertion that every declared variant is covered — so a new spelling fails loudly instead of being silently skipped.
