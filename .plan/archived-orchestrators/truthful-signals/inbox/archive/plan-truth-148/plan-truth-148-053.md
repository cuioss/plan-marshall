envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:05:48Z

# Candidate lesson: dict() over parsed rows dropped a duplicate before the routing assertion saw it

- source_signal: automatic-review / CodeRabbit inline (PR #1488), second review round
- record_id: 4e88ca (comment PRRC_kwDOQ3xasM7uteDa)
- file: test/plan-marshall/phase-6-finalize/test_loop_back_outcome.py:98
- resolution: fixed via TASK-026 — helper returns parsed rows, routing asserted over every row, state set derived from those rows, docstring corrected

## What happened

`dict(_STATE_OUTCOME_ROW.findall(section))` keeps only the LAST row per state, so a duplicate row is dropped before the routing assertion sees it — while the docstring claimed the check runs per state over rows derived from the table. If a state first records `failed` and later records `loop_back`, the test passes although the workflow documents a terminal route.

Note that this is the SECOND defect found in the fix for R04: TASK-023 derived the population from a new structured declaration, and the derivation itself silently deduplicated. It was latent (a sweep found exactly 3 rows for the 3 states, none duplicated) and was fixed anyway because the over-claim is the defect class the PR was about.

## Candidate rule

A parse-then-`dict()` pipeline is a silent deduplication that discards exactly the anomaly a table-consistency check exists to catch. Assert over the PARSED ROWS, derive the membership set from them, and keep the docstring's claim equal to what the code checks. Also: fixing a derivation defect by introducing a derivation is only half the work — the new derivation needs the same scrutiny.
