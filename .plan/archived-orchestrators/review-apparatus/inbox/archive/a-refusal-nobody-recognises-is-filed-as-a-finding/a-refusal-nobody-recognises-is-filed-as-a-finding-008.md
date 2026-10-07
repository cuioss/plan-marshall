envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T07:23:44Z

component=plan-marshall:phase-6-finalize
category=improvement
title=pre-submission-self-review does not pass --iteration on qgate add, making the per-round yield curve unrecoverable

# The one number needed to decide when to stop reviewing was made unrecoverable by omitting an argument that already exists

## Context

`pre-submission-self-review` ran 7 rounds and persisted 15 findings to `qgate-6-finalize.jsonl`. Not one carries an `iteration` value. `qgate list --iteration N` returns nothing useful for this plan.

Reconstructing round attribution required inferring it from timestamp clustering, and the inference does not close: round 3's own `[STATUS]` line claims "5 findings in 3 classes" and no finding is timestamped in that window, so the store's 15 is a floor over a population the step itself reported as at least 20. Rounds 3, 4 and 6 cannot be separated at all.

## Root cause

`manage-findings qgate add` already declares `--iteration N` and documents it as "which verification cycle produced the finding". The self-review workflow never passes it.

## Proposed action

Pass `--iteration {round}` on every `qgate add` the self-review makes. This is free — the parameter exists and the round number is in hand at the call site.

The payoff is a stopping rule that can be evaluated instead of argued: for this plan, the decisive fact is that the second behavioural defect (`2fb610` — `classify_bot` gated behind `bot in refused`, with a test that pinned the defect) surfaced at **round 6 of 7**. A yield curve keyed on defect CLASS rather than defect COUNT would have justified continuing past round 5 mechanically. Without `--iteration`, that argument can only be made by hand, after the fact, from a store that does not reconcile.

## Evidence

- aspect: logging_gap_analysis gap LG2 and LG3
- aspect: llm_to_script_opportunities candidate O6
- `qgate list --phase 6-finalize`: 15 findings, no iteration values, five timestamp clusters for seven rounds
