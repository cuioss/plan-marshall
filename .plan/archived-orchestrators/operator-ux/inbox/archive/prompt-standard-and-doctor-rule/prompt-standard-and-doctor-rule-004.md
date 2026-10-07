envelope_version=1
sender_type=plan
sender_id=prompt-standard-and-doctor-rule
epic=operator-ux
kind=candidate-lesson
created=2026-09-02T13:41:19Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=prompt-standard-and-doctor-rule
recurrence_of=2026-08-25-09-007

# Finalize carries 52% of plan tokens; the self-review loop is a plurality of it, not the whole

## Context

**Second independent instance.** Active global lesson `2026-08-25-09-007` recorded finalize cost concentration on 2026-08-25 and is still unapplied; this run's `lessons-housekeeping` retained it on 2026-09-01 as *"bound self-review re-firing - finalize cost surface untouched by this plan, no coverage"*.

Measured on this plan — a `single_module` + `feature` change touching 10 files across 2 deliverables and 3 tasks:

| Phase | Wall | Worked | Tokens | Share |
|---|---|---|---|---|
| 2-refine | 8m13s | 7m18s | 157,961 | 4% |
| 3-outline | 36m33s | 17m25s | 551,119 | 16% |
| 4-plan | 27m18s | 14m23s | 418,644 | 12% |
| 5-execute | 1h9m | 52m30s | 562,879 | 16% |
| **6-finalize** | unclosed | **1h12m** | **1,848,990** | **52%** |

The `single_module + feature` anchors are 1.0M warning / 1.6M error. Observed 3,539,593 tokens — **2.2x the error anchor** — and 149 wall minutes against a 120-minute error anchor. All four Section-1 fallback ratios also trip. Because `6-finalize` never closed an `end_time`, every one of these is a **floor**.

The run narrative assumed the self-review loop consumed "the large majority" of the finalize spend. It did not. Its four recorded dispatch rows carry **677,934 tokens — 43% of the phase dispatch-boundary total and 37% of the phase's dispatched tokens**. It is the largest single consumer by a wide margin, but the other 57% is spread across ten further rows: three deploy/sync/housekeeping steps, `automatic-review` (168,162 with a 673s `blocked_user_review`), `finalize-step-simplify`, `plugin-doctor` and `create-pr`.

## Root cause

Two contributors that need different remedies:

1. **Productive-but-avoidable re-firing.** Rounds 3 and 4 of self-review (7 of 11 findings) exist substantially because rounds 1 and 2 reworded where their own finding text prescribed deletion — see the companion candidate on that. That is roughly 330K recorded tokens of avoidable spend, plus one round that recorded no boundary row at all.
2. **Structural finalize breadth.** 23 finalize steps ran under a `standard` posture on a 10-file change. Seven were dispatched; nine ran inline with zero recorded token attribution. The overrun is not attributable to the self-review loop alone, so bounding that loop does not close it.

## Proposed action

Judged on the evidence: the eleven findings were all genuine false claims in prose this plan was shipping, in a plan whose entire subject is prose that over-claims what code enforces. Shipping them would have been the exact failure the plan exists to prevent, and no external reviewer found any of them. The *loop* was proportionate; two of its five *rounds* were not.

So: do not cap the round count. Instead
1. fix the fix-discipline defect (companion candidate) — that is where the avoidable spend is;
2. get a `Billing (cost)` figure for finalize before tuning anything else. `totals_billing_weighted_total` is `0` with `population_count: 0` on this plan because the four context-load columns were `unmeasured` on all 12 dispatch rows and `enrich` never ran. Every judgement above is on dispatched tokens only;
3. reconsider whether a `standard` posture should schedule 23 finalize steps for a 2-deliverable, 10-file change.

## Evidence

- aspect: plan_efficiency — `totals.tokens=3539593`, error anchor 1.6M crossed 2.2x; `max_phase_token_share=0.52`; all four fallback ratios tripped; every total a floor (`n=5/6`)
- aspect: plan_efficiency — `self_review_recorded_tokens=677934` of `dispatch_boundary_total=1578291`; `tokens_per_self_review_finding=61630`
- aspect: log_analysis — `context_position_cost.measured_rows: 0` of 12; `totals_billing_weighted_total: 0` with `population_count: 0`
- aspect: execution_context_dispatch_audit — 7 dispatched / 9 `ran_inline` of 16 finalize steps
- prior instance: global lesson `2026-08-25-09-007` (active, unapplied), decision `8a0a7f`
