envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=candidate-lesson
created=2026-09-29T13:39:43Z

component=plan-marshall:phase-6-finalize
category=improvement

# Measure self-review convergence per round instead of counting loop-backs

## Context

In plan-12-tool-triage `pre-submission-self-review` fired 13 times and returned `loop_back` in 10 of them. It breached the loop-back ceiling of 5 at iteration 6. The operator authorized iterations 6 through 12 one at a time, then closed the step by override (`may_close: operator_override`) without a clean full-scope `may_close=yes` pass. Each fix round produced new findings for the next round. The round-12 fix deleted doc content that a whole-tree verb-doc test depended on: the scoped fix-run did not catch it, the pre-push quality gate did, and fix c0d328 restored it in dd28b5002. 6-finalize carried 59% of the plan's 19.85M tokens.

## Root cause

The only stop signal is a round count. Nothing measures whether a round's findings were caused by the previous round's fix (non-convergence) or already existed (real residue), so the operator decides each extra round blind. Fix-runs verify at module scope, so a deletion that breaks a whole-tree consumer passes the fix-run and surfaces later.

## Proposed action

For each round, compute the share of findings that fall inside the previous fix commit's diff hunks and report it with the loop-back request. At the ceiling, surface that split in the operator prompt. A fix-run that deletes doc or contract content should run the whole-tree tests that reference the deleted text before it returns.

## Evidence

- aspect: plan_efficiency — max_phase_token_share=0.59, 6-finalize=11710620 (boundary floor)
- aspect: chat_history_analysis — 7 operator-authorized rounds beyond max_iterations=5, closed by operator override
- aspect: logging_gap_analysis — 20 returned_with_findings dispatch rows in 6-finalize
- status.json phase_steps.pre-submission-self-review firing_count=13; work.log "Loop-back ceiling breached — ... requested iteration 6 against a ceiling of 5"
