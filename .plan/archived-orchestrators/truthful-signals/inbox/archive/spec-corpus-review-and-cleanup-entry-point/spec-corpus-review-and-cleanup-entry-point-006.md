envelope_version=1
sender_type=plan
sender_id=spec-corpus-review-and-cleanup-entry-point
epic=truthful-signals
kind=candidate-lesson
created=2026-08-22T16:18:16Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=spec-corpus-review-and-cleanup-entry-point
source_aspects=plan_efficiency,log_analysis,routing_decisions

# Finalize consumed 59% of plan tokens against 17% for the phase that did the work

## Context

This plan is `scope_estimate: single_module`, `change_type: feature`, and landed 16 files. Its measured token distribution:

| Phase | Tokens | Share | Tool uses |
|-------|-------:|------:|----------:|
| 1-init | (inline, unmeasured) | — | — |
| 2-refine | 143,813 | 2.6% | 68 |
| 3-outline | 742,244 | 13.7% | 238 |
| 4-plan | 417,078 | 7.7% | 136 |
| 5-execute | 911,368 | 16.8% | 460 |
| **6-finalize** | **3,218,469** | **59.2%** | **828** |
| Total | 5,432,972 (n=5/6, a floor) | | 1,730 |

The `single_module + feature` anchor warns at 1.0M tokens / 75 min and errors at 1.6M / 120 min. The plan came in at **3.4× the error anchor** on tokens and **3.6×** on worked time (427 minutes). All four fallback ratios also trip: 388K tokens per declared modified file (7.8× the 50K watch threshold), 1,832 worked seconds per task, 0.59 max-phase concentration, 604K per deliverable.

Where finalize's time actually went, from the plan's own script-execution cost rollup:

| Script | Calls | Cumulative | Share |
|--------|------:|-----------:|------:|
| `pyproject_build` | 144 | 4h27m | 62.4% |
| `tools-integration-ci:ci` | 25 | 1h12m | 16.8% |
| `ci_complete_precondition` | 8 | 56m | 13.1% |
| **builds + CI + CI-polling** | | | **92.3%** |

144 build invocations for a 16-file change. Three CI runs were archived (31339017325, 31359625036, 31362783120). Separately, 49% of measured wall clock (3h49m of 7h47m) was idle.

## Root cause

Not a single defect — a structural distribution. Two identified contributors, both recorded:

1. The operator's mid-finalize "Fix it in this plan" disposition of finding `5b1178` bought +1 execute cycle and +3 orchestrator-tier builds, and the cost was declared before the choice was made. That is the system working as designed.
2. The pre-submission self-review reached **round 4** before closing, at roughly 200K per round by the gate's own estimate.

What is missing is any feedback loop: the manifest's `execution_profile_cost_preview` was never recorded, so `check-routing-decisions` reported `comparison: not_attempted` — the plan had no predicted cost to compare its 1.7M execution-log spend against. Nothing in the run could observe that finalize was running 3.4× over its anchor while it was happening.

## Proposed action

1. Record `status.metadata.execution_profile_cost_preview` at manifest-compose time so the predicted-versus-actual comparison the routing-decisions aspect already implements has an input. Today that comparison is permanently `not_attempted`.
2. Consider surfacing the anchor breach *during* finalize rather than only in the retrospective. The anchor table, the phase totals, and the accumulators all exist mid-run; a plan crossing its error anchor by 3× is knowable before it crosses it by 3.4×.
3. Investigate the 144-build count specifically. Steps that re-run a build after each fix round multiply quickly, and at 62% of script wall time this is the largest single lever in the plan.

## Evidence

- aspect: plan_efficiency — `[BUDGET] single_module feature exceeded the 1.6M-token error anchor by 3.4x (5.43M observed, and the total is a FLOOR at n=5/6)`; all four fallback ratios also tripped
- aspect: log_analysis — `script_cost_rollup`: build 62.357%, ci 16.831%, ci_complete_precondition 13.062% of 25,745,510 ms total
- aspect: routing_decisions — `cost_preview.comparison: not_attempted`, `comparison_reason: no cost preview recorded in status.metadata.execution_profile_cost_preview`
- aspect: chat_history_analysis — both operator gates declared their cost and both were answered toward the more expensive branch
- corroborating: 20 finalize dispatches, all terminating `step_complete` — zero error, zero retryable. None of this spend was waste in the failure sense; it was the cost of the work as configured
