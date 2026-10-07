envelope_version=1
sender_type=plan
sender_id=orchestrator-inbox-and-landing-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T16:54:35Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=orchestrator-inbox-and-landing-residue
source_aspects=plan_efficiency,log_analysis,chat_history_analysis

# Bound finalize step re-fires - self-review burned 7 firings, 6 failed

## Context

This plan is `scope_estimate=single_module`, `change_type=bug_fix`. Its anchor row warns at 800K tokens and errors at 1.3M. It consumed **6,443,862** dispatched tokens — roughly 5x the error anchor — and that figure is a **floor**, because `1-init` carries no token record and `6-finalize` was never closed by `end-phase`.

The concentration is in finalize:

| Phase | Tokens | Share |
|-------|--------:|------:|
| 2-refine | 140,723 | 2% |
| 3-outline | 828,391 | 13% |
| 4-plan | 523,019 | 8% |
| 5-execute | 1,017,359 | 16% |
| **6-finalize** | **3,934,370** | **61%** |

Finalize outspent execute by 3.9x on a bug-fix plan.

**Re-fire is the driver.** From `status.metadata.phase_steps["6-finalize"]`:

- `pre-submission-self-review` — `firing_count: 7`, `prior_firings: [failed, failed, done, failed, failed, failed]`
- `push` — `firing_count: 3` (1 failed)
- `pre-push-quality-gate`, `project:finalize-step-plugin-doctor`, `ci-verify`, `automatic-review` — `firing_count: 2` each

**Error-terminated dispatch spend.** The finalize dispatch ledger records 4 rows with `termination_cause: error` totalling **869,753 tokens** (22% of the phase) with `retryable_total_tokens: 0` — none of it recoverable infrastructure loss, all of it terminal waste.

**Operator cost.** 6 of the 10 operator turns in the plan's first session were bare prods to restart a stalled finalize (`continue` x3, `continue finalize`, `why did you stop? continue with finalize to the end`, `retry`, `status?`).

## Root cause

Nothing bounds how many times a finalize step may re-fire, and nothing accumulates the cost of its re-fires against a budget. Each firing is a fresh `execution-context` envelope charged in full, so a step that fails six times before succeeding costs seven envelopes and no gate observes the total.

The self-review case is the clearest: round 7 found a **substantive** finding (`653c69` — the payload spec's `pr` row still said `#NNN`/`n/a` while the same document already routed every failed read to `unknown`). Six prior rounds over the same 17 files did not surface it. So the re-fires were not converging; the 7th round found something the first six missed on identical input, which is a detector-consistency problem rather than a work-remaining problem.

## Proposed action

- Record cumulative per-step re-fire spend and surface it at the step boundary, so `firing_count: 7` carries its token cost rather than only its ordinal.
- Add a re-fire ceiling per step (configurable, defaulting low) that escalates to the operator with the accumulated cost rather than silently re-firing.
- Investigate `pre-submission-self-review` non-determinism separately: six clean-or-failed rounds followed by a substantive 7th-round finding on unchanged input is a signal about the detector, not about the code.
- Add `manage-status list-step-refires --plan-id --phase` so the re-fire population is queryable instead of being read out of `status.json` by eye.

## Evidence

- aspect: plan_efficiency — `[BUDGET] single_module bug-fix exceeded the 1.3M-token error anchor by ~5x (6.44M observed, and that figure is a floor)`, `max_phase_token_share=0.61`
- aspect: log_analysis — `6-finalize: error_total_tokens: 869753, retryable_total_tokens: 0`, 15 dispatch rows
- `manage-status read` — `pre-submission-self-review: firing_count: 7, prior_firings[6]{outcome}: failed failed done failed failed failed`
- aspect: chat_history_analysis — 6 of 10 operator turns were bare resume prods; self-review round 7 finding `653c69` quoted verbatim in the gate decision
