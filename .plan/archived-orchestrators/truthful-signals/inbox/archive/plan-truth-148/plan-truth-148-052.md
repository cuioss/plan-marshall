envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:05:45Z

# Candidate lesson: a body-wide substring test let unrelated prose satisfy the guard

- source_signal: automatic-review / CodeRabbit inline (PR #1488), severity Major
- record_id: e6d384 (comment PRRC_kwDOQ3xasM7uheEb)
- file: test/plan-marshall/phase-6-finalize/test_pre_submission_self_review_verdict.py:951
- resolution: fixed via TASK-024, with a deliberate deviation from the proposed diff

## What happened

The detector accepted `may_close: yes` ANYWHERE in the branch body, so a branch could record `done` without using that answer as its selector as long as unrelated prose mentioned the token.

The deviation is worth recording: the bot's proposed diff narrowed the check to `_branch_label` alone, which would have asserted the wrong thing, because the stop answer lives in the branch PRECONDITION, not in the label. The run took the second form the comment offered — label plus explicit precondition — keeping the quantification over the derived branch set intact.

## Candidate rule

Check a guard's predicate against the scenario the guard exists for; a body-wide substring match is presence, not selection. And a review bot's committable suggestion is a proposal, not the finding: when the suggestion would assert the wrong property, take the finding and reject the diff, recording why.
