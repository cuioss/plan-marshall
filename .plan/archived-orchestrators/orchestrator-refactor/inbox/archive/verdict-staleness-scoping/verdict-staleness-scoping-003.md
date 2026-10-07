envelope_version=1
sender_type=plan
sender_id=verdict-staleness-scoping
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-22T21:28:25Z

# Finalize spent 1.94M tokens on a 6-file bug fix, matching execute

## Metadata

- component: `plan-marshall:phase-6-finalize`
- category: improvement
- confidence: high
- observed_in_plan: verdict-staleness-scoping

## Context

A `single_module` / `bug_fix` plan with a 6-file realized footprint and 2 deliverables
consumed 5,125,803 tokens across 5 measured phases. The plan-efficiency anchor row
`single_module + bug_fix` warns at 800K and errors at 1.3M; the observed total crossed the
error column by 3.9x, and the worked time of 172 minutes crossed the same row's 90-minute
error column. The phase split is the notable part: `6-finalize` took 1,938,678 tokens against
`5-execute`'s 1,950,288 — the gate cost essentially as much as the change it was gating.

## Root cause

Loop-back churn plus CI/review waiting dominate. `loop_back_iteration` reached 4;
`pre-submission-self-review` fired 6 times (2 loop_back, 1 failed), and six further finalize
steps carry `firing_count: 3`. Measured script cost is 89.9% owned by three notations —
`tools-integration-ci` 43.5%, `ci_complete_precondition` 40.5%, `github_re_review` 5.9% — all
three hitting the 600s ceiling. Each loop-back re-runs the full downstream gate rather than
only the steps whose inputs moved.

## Proposed action

Treat finalize re-entry cost as a first-class budget. Two concrete levers worth sizing before
staging: (a) scope a loop-back re-fire to the steps whose inputs actually changed, using the
per-step `head_at_completion` already recorded in `status.metadata.phase_steps`; (b) confirm
whether the three ceiling-hitting CI notations are genuinely waiting or re-polling work
already done. Size each lever before staging it.

## Evidence

- aspect: plan_efficiency — `[BUDGET]` error at `single_module+bug_fix error at 1.3M tokens`; `tokens_per_file_modified=854300`
- aspect: plan_efficiency — `6-finalize=1938678` against `5-execute=1950288`
- aspect: log_analysis — `script_cost_rollup` ranks `ci` (43.53%), `ci_complete_precondition` (40.54%), `github_re_review` (5.94%) over 13,234s of logged script time
- source: `status.metadata.phase_steps["6-finalize"]` — `firing_count: 3` on six steps, `firing_count: 6` on `pre-submission-self-review`
