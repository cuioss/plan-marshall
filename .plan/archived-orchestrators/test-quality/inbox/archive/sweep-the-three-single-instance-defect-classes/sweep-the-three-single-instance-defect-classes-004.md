envelope_version=1
sender_type=plan
sender_id=sweep-the-three-single-instance-defect-classes
epic=test-quality
kind=candidate-lesson
created=2026-09-14T03:21:47Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=sweep-the-three-single-instance-defect-classes
source_aspects=plan_efficiency,logging_gap_analysis,log_analysis

# Bound finalize loop-back rounds - 5 rounds outcost the whole execute phase

## Context

The plan's product is 87 changed files, almost all of them small test-file edits. It cost 9,882,263 tokens against a `multi_module + tech_debt` error anchor of 2.5M — roughly 4x over — and 748 minutes of wall clock against a 180-minute error anchor. Both figures are floors, because `6-finalize` never closed.

The distribution is the finding. `6-finalize` alone took 5,441,503 tokens — 55% of the total — against `5-execute`'s 3,072,253. Finalize cost more than the work it was finalizing. Behind that: 27 finalize dispatches, 6 of them `returned_with_findings`, `loop_back_iteration` at 5, and `pre-submission-self-review` with a `firing_count` of 7 across two recorded `loop_back` outcomes. Four other steps each fired 4 times.

Where the wall time went is a separate answer from where the tokens went. Of 16,009,410 ms of script wall time, 68.1% sits in two CI-polling notations — `tools-integration-ci:ci` (32 calls, 5,457,300 ms) and `phase-6-finalize:ci_complete_precondition` (26 calls, 5,447,910 ms) — against 24.2% in the build wrapper. The verification was cheap; the review and CI round-trips were not.

## Root cause

Nothing bounds the loop-back round count, and each round re-fires the full remaining step tail. A review step that files findings sends control back to `6-finalize`, the re-entry replays the steps after it, and every replay pays another CI wait plus another review-bot round. Five rounds of that is a multiplicative cost on a plan whose changes are individually trivial. The `returned_with_findings` terminations are productive in isolation — the dispatches did find things — but no mechanism asks whether the fifth round is still buying enough to justify another full tail.

## Proposed action

Introduce a loop-back round budget for `6-finalize`, configurable like the existing finalize budgets (`merge_queue_wait_budget_seconds`, `review_completion_poll_timeout_seconds` are the precedent), and surface the accrued cost at each round boundary so the decision to spend another round is taken against a visible number. A plan running unattended — as this one was, under a single `Continue (recommended)` gate answer — has no other point at which the cost becomes visible before the retrospective. Consider also whether a replay needs to re-run the CI-polling steps in full, or whether an unchanged HEAD can short-circuit them.

## Evidence

- aspect: plan_efficiency — `total_tokens=9882263` against `multi_module+tech_debt` error anchor 2.5M; `max_phase_token_share=0.55`, `dominant_phase=6-finalize=5441503`
- aspect: plan_efficiency — `ci_polling_share_pct: 68.1` of 16,009,410 ms script wall time
- aspect: logging_gap_analysis — 6-finalize: 27 dispatch rows, 21 `step_complete`, 6 `returned_with_findings`
- status.metadata — `loop_back_iteration: 5`; `pre-submission-self-review.firing_count: 7`
