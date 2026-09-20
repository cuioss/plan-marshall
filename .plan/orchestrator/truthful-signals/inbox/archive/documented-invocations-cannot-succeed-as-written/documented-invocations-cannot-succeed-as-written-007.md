envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T18:49:56Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=medium
source_plan=documented-invocations-cannot-succeed-as-written
source_pr=1386

# Finalize outspent every other phase combined on a bug-fix plan

## Context

Phase token totals for a `multi_module` + `bug_fix` plan that changed 28 files
across 4 deliverables and 12 tasks:

| phase | tokens |
|---|---|
| 1-init | not recorded |
| 2-refine | 370,958 |
| 3-outline | 685,960 |
| 4-plan | 452,939 |
| 5-execute | 1,323,927 |
| 6-finalize | 3,011,257 |

`6-finalize` alone (3,011,257) exceeds all five other phases combined
(2,833,784); `max_phase_token_share` is 0.52. The total of 5,845,041 crosses the
`multi_module + bug_fix` ERROR anchor of 2.0M by 2.9x, and worked time of 298.9
minutes crosses that row's 150-minute error column.

## Root cause

Three compounding contributors, all inside finalize:

1. `pre-submission-self-review` fired FIVE times (`prior_firings: [failed,
   failed, failed, done]`, current `done`). The three failures account for
   `error_total_tokens: 737,877` — 12.6% of the plan's entire spend — with
   `retryable_total_tokens: 0`, so none of it is infrastructure that a re-run
   would have recovered.
2. The phase-6 to phase-5 loop-back re-fired the whole settle band: five
   finalize steps carry `firing_count >= 2` and `pre-push-quality-gate` reached 3.
3. 75,518 stale temp files / 714 MB of pytest residue inflated a `module-tests`
   run to 1,519s; after the sweep the same command took 740s.

## Proposed action

Attack the largest term first: a step that can fail three times before
succeeding is spending most of its budget on rounds that return nothing. Give
`pre-submission-self-review` a bounded failure budget with a distinguishable
terminal state, so the third identical failure escalates instead of re-firing.
Separately, sweeping the pytest basetemp residue before a whole-tree run is a
2x saving on the single longest command in the plan.

## Evidence

- aspect: plan_efficiency — `[BUDGET] multi_module bug_fix crossed the
  2.0M-token ERROR anchor, 5.85M observed`; `max_phase_token_share=0.52`
- aspect: logging_gap_analysis — `6-finalize` distribution: 11 `step_complete`,
  3 `error`; `error_total_tokens: 737877`, `retryable_total_tokens: 0`
- run observation: `module-tests` 1,519s before the temp sweep, 740s after
