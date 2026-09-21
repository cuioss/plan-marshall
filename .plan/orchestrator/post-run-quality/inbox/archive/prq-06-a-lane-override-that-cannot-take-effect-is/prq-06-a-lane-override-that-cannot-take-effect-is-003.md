envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:37:24Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=prq-06-a-lane-override-that-cannot-take-effect-is
source_aspects=plan_efficiency,logging_gap_analysis,chat_history_analysis

# Finalize re-firing, not execution, is where half this plan's tokens went

## Context

A single-module `tech_debt` change touching 26 files cost 8,444,415 tokens against an anchor that warns at 1.0M and errors at 1.6M — 5.3x the error column. The split says where it went:

| Phase | Tokens | Share |
|-------|--------|-------|
| 5-execute | 2,641,751 | 31% |
| 6-finalize | 4,232,432 (boundary floor) | 50% |
| all others | 1,570,232 | 19% |

Finalize cost more than the work it was finalizing. The driver is re-firing, not any single expensive step: 47 recorded firings across 9 finalize steps where 9 would suffice — 38 excess firings — over 6 loop-back iterations.

| Step | firing_count | Last reported outcome |
|------|-------------:|-----------------------|
| finalize-step-simplify | 12 | "0 edits, 4 findings" |
| pre-submission-self-review | 9 | "clean: 103 candidates examined, no check matched" (7 of 8 prior firings were `loop_back`) |
| project:finalize-step-lessons-housekeeping | 8 | "0 rm, 0 promo, 0 adapt, 2 keep" |
| project:finalize-step-plugin-doctor | 7 | "clean: 5 skills gated" |

## Root cause

Every loop-back re-fires the whole ordered prefix of finalize steps, at full dispatch cost, with no convergence check in front of any of them. `lessons-housekeeping` reported `0 rm, 0 promo, 0 adapt` on its final run and evidently on most of the prior seven; `finalize-step-simplify` made 0 edits on its final run of twelve. These steps had converged long before the loop-backs stopped, yet each re-fire paid a fresh envelope.

The loop-backs themselves were not misfires — all 6 originate in 6-finalize, none reaches back to `2-refine` or `5-execute`, and 5 finalize dispatches are stamped `returned_with_findings` (a productive non-completion). The request was well refined; the cost is purely in re-running settled work.

## Proposed action

Gate re-firing on a cheap idempotence probe. Several shapes are available and can be combined:

1. **HEAD-bound skip.** Several steps already stamp `head_at_completion`. When a step's `head_at_completion` equals the current HEAD *and* its last outcome was `done` with a no-work `facts` block, skip the re-fire and record `outcome: done, basis: unchanged-head` without dispatching.
2. **Work-performed flag.** `finalize-step-sync-baseline` and `branch-cleanup` already publish `work_performed`. Extend that to every step and treat two consecutive `work_performed: false` firings as convergence for that step until HEAD moves.
3. **Cap the prefix.** On loop-back iteration N, re-fire only the steps whose inputs the loop-back actually invalidated, rather than the whole prefix.

## Evidence

- aspect: plan_efficiency — `[BUDGET] single_module tech_debt crossed the 1.6M-token error anchor by 5.3x`; `max_phase_token_share=0.50`, `dominant_phase=6-finalize=4232432`
- `status.metadata.phase_steps["6-finalize"]` — 47 total firings across 9 steps, `loop_back_iteration: 6`
- aspect: logging_gap_analysis — 25 finalize dispatch-boundary rows, 20 `step_complete` + 5 `returned_with_findings`
- aspect: chat_history_analysis — all 6 loop-backs originate in 6-finalize; none reaches `2-refine`
