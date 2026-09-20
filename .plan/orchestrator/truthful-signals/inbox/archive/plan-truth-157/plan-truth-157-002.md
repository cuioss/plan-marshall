envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:50:41Z

# Report remaining loop-back budget before entering the pre-merge barrier

component: plan-marshall:phase-6-finalize
category: improvement
confidence: high
source_plan: plan-truth-157
source_aspects: plan_efficiency, chat_history_analysis, invariant_summary

## Context

All five permitted loop-backs were consumed by a single finalize step. `pre-submission-self-review` fired
six times, returning `loop_back` to `6-finalize` on five of them and `done` on the sixth, taking
`loop_back_iteration` to 5 — the configured ceiling. No other step returned a loop-back.

The run then entered `branch-cleanup` with its `pre_merge_comment_barrier: fail_into_loopback` and zero
remaining budget. A single unresolved comment at that barrier would have forced the ceiling-breach halt. The
barrier held only because the late CodeRabbit triage of two Major findings produced no fix tasks — an
outcome the run did not control and could not have predicted when it spent its fifth loop-back.

The cost side has the same root cause. `6-finalize` spent 3,548,829 of the plan's 6,297,406 tokens
(56 percent — more than phases 1 through 5 combined) on a change whose realized footprint is 10 files. All
four Section-1 fallback ratio thresholds tripped for the `single_module + enhancement` pair:
`tokens_per_file_modified=699711.78` (threshold 50,000), `total_tokens_per_deliverable=1049567.67`
(threshold 500,000), `max_phase_token_share=0.56` (threshold 0.50), and
`worked_seconds_per_task=3490.28` (threshold 900, itself unanchored for worked time).

## Root cause

The remaining loop-back budget is tracked (`loop_back_iteration` against `max_iterations`) but is not
surfaced at the decision point where it matters. A step that returns `loop_back` sees its own outcome; the
run does not report how much budget is left before entering a later step whose failure mode is also a
loop-back. The ceiling is therefore discovered at the breach rather than approached visibly.

## Proposed action

Surface `remaining_loop_backs` in the step-transition output before any `fail_into_loopback` barrier is
entered, so a run arriving at the merge with zero budget is visible ahead of the barrier. This is a
reporting change, not a policy change: it does not raise the ceiling, relax the barrier, or alter what any
step decides — it makes the budget state legible at the point a reader would act on it.

## Evidence

- aspect: invariant_summary / status.metadata — `phase_steps["6-finalize"]["pre-submission-self-review"]`
  records `prior_firings` of five `loop_back` plus one `done`, `firing_count: 6`, and
  `loop_back_iteration: 5`
- aspect: plan_efficiency — `6-finalize=3548829` is the dominant phase at `max_phase_token_share=0.56`;
  all four fallback thresholds tripped
- aspect: chat_history_analysis — the operator pre-authorised both branches of the final triage in advance,
  including the designed HALT, which is what a run with no remaining budget requires from its operator

## Related prior observation

This is a recurrence of a known archetype in which one review-shaped finalize step consumes the entire
loop-back allowance. Recorded here with this plan's counts rather than restated; the orchestrator holds the
cross-plan view needed to decide whether the archetype warrants more than a reporting change.
