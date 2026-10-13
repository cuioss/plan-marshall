envelope_version=1
sender_type=plan
sender_id=plan-lb-38-review-gate-and-empty-scope
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T23:06:04Z

component=plan-marshall:phase-5-execute
category=improvement

# Run root-level test guards in the per-deliverable build, not first at pre-push

## Context

In plan-lb-38 every per-deliverable module-tests run was green, yet pre-push-quality-gate failed twice. The root-level guard test/test_harness_shape_guards.py (R5 non-vacuity for runtime-derived parametrize bindings) flagged three new parametrize derivations in test_comments_stage_filters.py and test_re_review_strategy_match.py. A finalize leaf fixed them with module-level asserts (commit 82b128733), which also re-fired lessons-housekeeping, plugin-doctor and the self-review on the new head.

## Root cause

Scoped module-tests runs (module-tests plan-marshall/{unit}) do not collect the root-level test/*.py guards, and the build wrapper exposes no narrow form for them, so a guard violation surfaces only at the whole-tree gate. This is a recurrence of lesson 2026-10-11-16-003, which lessons-housekeeping kept as still uncovered on this plan.

## Proposed action

Make the per-deliverable verification include the root-level shape guards (or a selectable build-pyproject target for them that a scoped run can add), so a guard violation is caught in execute rather than after push preparation. Merge with lesson 2026-10-11-16-003 rather than filing a parallel lesson.

## Evidence

- status.json: pre-push-quality-gate prior_firings failed, failed before done (firing_count 3)
- aspect: llm_to_script_opportunities - a leaf ran the R5 predicate via python3 -c because the wrapper has no narrow form
- aspect: chat_history_analysis - lessons-housekeeping delta notes the new commit is another occurrence of lesson 2026-10-11-16-003
- aspect: plan_efficiency - finalize consumed 3.79M tokens (42% of the plan), inflated by the re-fired finalize steps
