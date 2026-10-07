envelope_version=1
sender_type=plan
sender_id=required-reviewer-returns-empty-list
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T16:33:28Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-09-05
bundle=plan-marshall

# Bound finalize step re-firing: 32 re-firings cost 71% of this plan's tokens

## Context

The plan shipped three files — two standards documents and one test — and consumed
8,108,032 dispatched tokens. `6-finalize` accounted for 5,728,142 of them: 71% of the
whole plan, against 1,028,619 for `5-execute`, the phase that did the work.

The finalize phase ran 4 loop-back iterations (`status.metadata.loop_back_iteration: 4`)
and re-fired six steps:

| Step | firing_count |
|---|---|
| automatic-review | 7 |
| pre-submission-self-review | 6 |
| project:finalize-step-plugin-doctor | 6 |
| finalize-step-simplify | 5 |
| ci-verify | 4 |
| pre-push-quality-gate | 4 |

28 dispatch-boundary rows were recorded for `6-finalize`: 22 `step_complete`,
5 `returned_with_findings`, 1 `blocked_user_review`.

## Root cause

The re-firing is individually justified and collectively unbounded. Every one of the five
`returned_with_findings` terminations is a PRODUCTIVE loop-back by contract — a step
examined its surface, filed findings, and sent control upstream — and the contract
correctly excludes that cause from the agent-initiated-re-dispatch threshold. Zero tokens
were spent on `error` or on retryable terminations.

So no single firing is waste, and yet the aggregate is: each loop-back re-runs the whole
downstream tail rather than the step whose finding invalidated it. `finalize-step-simplify`
firing 5 times and reporting `0 edits, 0 findings` on its terminal firing is the visible
shape of that — a step re-executed because something upstream moved, not because its own
input changed.

Two of the four terminal-state signals also read clean while the plan was still cycling:
the terminal `pre-submission-self-review` reports `self-review clean: 32 candidates
examined, no check matched` with two `failed` firings in its history, so the final green
says nothing about the four iterations it took to reach it.

## Proposed action

This is submitted as an epic-level observation rather than a specific patch, because the
remedy is a design question the orchestrator holds context for. Concretely worth measuring:

1. Publish a per-finalize-run re-firing budget alongside the loop-back counter, so a run
   that has re-fired N steps M times is visible while it is happening rather than only in
   retrospect.
2. Scope a loop-back to the steps whose inputs actually moved, rather than replaying the
   tail from a fixed anchor — the five productive loop-backs cost 22 `step_complete`
   re-runs between them.
3. Treat `loop_back_iteration` as a first-class cost signal in the finalize report, since
   `outcome: done` on the terminal firing currently reads identically whether it took one
   iteration or four.

## Evidence

- aspect: plan_efficiency — `max_phase_token_share: 0.71`, `dominant_phase: 6-finalize=5728142`, `totals.tokens: 8108032`, `files_modified: 3`
- aspect: logging_gap_analysis — `6-finalize: 22 step_complete, 5 returned_with_findings, 1 blocked_user_review; error_total_tokens 0; retryable_total_tokens 0`
- `status.metadata.loop_back_iteration: 4` and the six `firing_count` values above
