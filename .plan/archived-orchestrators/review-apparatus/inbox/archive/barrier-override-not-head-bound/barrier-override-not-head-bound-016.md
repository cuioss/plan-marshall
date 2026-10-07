envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T13:18:02Z

# Self-review error path re-pays the whole envelope - 431K tokens on one step

component: plan-marshall:phase-6-finalize
category: improvement
confidence: medium

## Context

`pre-submission-self-review` on a nine-file bug fix:

| Run | Outcome | Tokens | Duration | Candidates |
|---|---|---:|---:|---:|
| 1 | error | 219,484 | 355s | 86 |
| 2 | executed | 212,423 | 511s | 106 |
| **Total** | | **431,907** | **866s** | |

That is 14.6% of the plan's entire measured 2,967,497-token spend on a single finalize step, roughly half
of it re-work.

The wider shape: 6-finalize consumed 1,299,699 tokens against 5-execute's 466,370 — a 2.8:1
ceremony-to-work ratio on a `single_module` `bug_fix`. The plan crossed the `single_module + bug_fix`
**error** anchor (1.3M tokens) by 2.3x.

## Root cause

There is no partial-result reuse across the error boundary. An envelope that fails at candidate 80 of 86
discards all 80 and restarts. The candidate set is deterministic and enumerable — it is recomputed from
the same diff — so the re-fire re-derives work it could have read.

Note the two runs are not identical: the candidate count grew 86 to 106 between them, so this is not a
pure replay and a naive cache would be wrong.

## Proposed action

Persist the self-review candidate set and per-candidate verdicts to `work/` as they are produced, keyed
by candidate identity rather than index. On re-fire, re-derive the candidate set (it may have grown) and
skip candidates already carrying a verdict for an unchanged source hash. This bounds re-work to the delta
rather than the whole envelope.

Secondary: the `single_module + bug_fix` calibration anchors in `plan-efficiency.md` (warning 800K, error
1.3M) may warrant re-checking against the current finalize pipeline — if a clean 9-file bug fix routinely
crosses the error column, the anchor is measuring the pipeline rather than the plan.

## Evidence

- aspect: plan_efficiency — `[BUDGET]` error findings on `total_tokens=2967497` and `duration_seconds=6995`
- aspect: plan_efficiency — `largest_single_line_item` note; `dominant_phase: 6-finalize=1299699`
- execution.toon `execution_log` — the two `pre-submission-self-review` rows
- decision.log 08:45:16 and 09:30:34 — candidate-count gate at 86 then 106
