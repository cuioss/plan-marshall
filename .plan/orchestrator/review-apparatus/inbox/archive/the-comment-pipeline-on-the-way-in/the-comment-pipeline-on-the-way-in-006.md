envelope_version=1
sender_type=plan
sender_id=the-comment-pipeline-on-the-way-in
epic=review-apparatus
kind=candidate-lesson
created=2026-09-24T16:20:29Z

component=plan-marshall:phase-6-finalize
category=improvement
title=Skip re-firing finalize steps whose scope a loop-back did not touch

# Skip re-firing finalize steps whose scope a loop-back did not touch

## Context

the-comment-pipeline-on-the-way-in looped back from finalize 9 times. Each pass re-fired the pre-push step chain: simplify 10 times, plugin-doctor 9 times, pre-submission-self-review 7 times (closed under operator waiver), pre-push-quality-gate 4 times and automatic-review 5 times. Finalize used 6.30M of 12.33M tokens (51%). The plan total is 6.2x the multi_module bug_fix error anchor.

## Root cause

A loop-back resets the whole finalize step list, and each step re-runs whatever the delta since its last completion was. `head_at_completion` is recorded for each step but is never used to decide whether the new delta touches that step's scope.

## Proposed action

Add a deterministic convergence check. For each finalize step with a recorded `head_at_completion`, diff `head_at_completion..HEAD`. When no changed path falls in the step's scope (e.g. plugin-doctor's skill set, or simplify's changed-code set), skip the step with a recorded `outcome: skipped` and the reason. Keep full re-runs for steps whose scope the loop-back touched.

## Evidence

- aspect: plan_efficiency: max_phase_token_share 0.51 (6-finalize=6296218); [BUDGET] error on tokens and worked time
- aspect: llm_to_script_opportunities: step-convergence check candidate, about 17 re-firings avoidable
