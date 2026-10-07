envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:45:54Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=plan-truth-148
source_aspects=plan_efficiency,chat_history_analysis,logging_gap_analysis,execution_context_dispatch_audit

# Cap the pre-submission self-review loop: 11 loop-backs cost 29 pct of the plan

## Context

`default:pre-submission-self-review` fired 15 times on plan-truth-148, 11 of them returning
`loop_back`, driving `loop_back_iteration` to 13. The 8 firings that carry a token row in the
execution log total 2,180,554 tokens. That figure is a FLOOR, not a total: 3 of the 11 loop_back
firings carry no row at all. Against the phase it is 85% of 6-finalize's 2,570,107 tokens, and
against the plan it is 29% of 7,434,299.

The chat reduction retained 4 operator turns out of 4,132 raw turns, and none of them falls inside
the loop. The convergence decision was therefore taken 15 times by the same party that authored the
work, with no human in the loop at any iteration.

## Root cause

The step has no iteration budget and no independent verifier. Each round re-derives its candidate
set from scratch — the plan directory holds 8 `self-review-candidates-round*.toon` artifacts
totalling 362 KB — so the marginal cost per round does not decay even as the findings thin out.
Nothing in the loop distinguishes "still finding real defects" from "re-examining the same surface".

## Proposed action

Three separable levers, in increasing order of cost:

1. Publish a token record for every loop_back firing, so the loop's cost is a measured total rather
   than a floor recovered from 8 of 11 rows.
2. Give the step a declared iteration budget whose exhaustion is an outcome the operator sees, not a
   silent continuation. `loop_back_iteration: 13` was reached without any surface announcing it.
3. Carry the candidate set forward between rounds instead of re-deriving it, so round N only examines
   what round N-1 changed.

## Evidence

- aspect: plan_efficiency — `measured_loop_back_tokens: 2180554` over `measured_rows: 8` of 11
  loop_back firings; `share_of_6_finalize: 0.85`, `share_of_plan: 0.29`
- aspect: chat_history_analysis — `operator_turn_count: 4` of `raw_turn_count: 4132`; no operator
  turn falls within the 13 loop_back iterations
- aspect: logging_gap_analysis — 8 of 13 finalize dispatches terminated `returned_with_findings`
- aspect: execution_context_dispatch_audit — `pre-submission-self-review` is one of only 3 finalize
  steps with any token evidence at all

## Recurrence

This is the archetype PLAN-TRUTH-089 recorded (finalize gate consuming 81% of a 13.9M run, self-review
firing 19 times). Deliverables 8 and 9 of plan-truth-148 set out to fix exactly this — establish
verifier independence, and ask the stop question of the verifier rather than of the author. Both
landed. Neither could govern the finalize run that shipped them, so the fix has not yet been observed
under load.
