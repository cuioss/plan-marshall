envelope_version=1
sender_type=plan
sender_id=plan-lr-07-lessons-verb-routing
epic=lessons-routing
kind=candidate-lesson
created=2026-09-23T06:56:40Z

# 6-finalize token/time budget overrun driven by repeated self-review loop-backs and multi-round bot re-review on the same fix

component: plan-marshall:pre-submission-self-review
category: improvement
confidence: high
source_aspects: plan-efficiency, logging-gap-analysis, chat-history-analysis

## Context

Plan `plan-lr-07-lessons-verb-routing` (single_module + bug_fix; anchor: warning at 800K tokens/60min, error at 1.3M tokens/90min) consumed 10.37M tokens and 297.6 worked-minutes — roughly 8x over the error anchor on tokens and over 3x on worked time. 79% of total tokens (8.22M) were spent inside `6-finalize` alone. The `pre-submission-self-review` step fired 12 times on this plan (`loop_back_iteration` reached 8), and after it settled, a formal-pipeline fix (TASK-4) for the resulting change still drew two further rounds of CodeRabbit findings against its own coverage gaps before the review-completeness barrier passed clean.

## Root cause

`phase-6-finalize.max_iterations` defaulted to 20, which tolerated far more self-review churn in practice than an operator watching the run wanted — the operator interrupted mid-run specifically to question a 10-round self-review loop and then directed lowering the default to 5 (landed in this same plan, `.plan/marshal.json`). Separately, each round of the loop (and each CodeRabbit re-review pass) surfaced genuinely new, non-trivial findings rather than converging quickly, suggesting the fix being self-reviewed was itself iteratively incomplete on each attempt rather than the loop over-firing on noise.

## Proposed action

The `max_iterations: 20 -> 5` change already shipped in this plan addresses the ceiling. Consider whether `pre-submission-self-review` (or the round-loop driving it) could surface a stronger operator-facing signal earlier — e.g. after round 3-4 without convergence — rather than requiring an interrupt-and-question, and whether a fix that draws 2+ follow-on CodeRabbit rounds on its own coverage gaps warrants a mandatory adversarial self-check step before the fix is considered complete.

## Evidence

- aspect: plan_efficiency — `[BUDGET] single_module bug-fix exceeded 1.3M-token error anchor (10.37M observed, ~8x over)`, `6-finalize=8221439` (79% of total)
- aspect: logging_gap_analysis — `DISPATCH_TERMINATION_CAUSE 6-finalize: 15 step_complete, 1 error` across 16 finalize-phase dispatch rows
- aspect: chat_history_analysis — operator pivot: "what are you doing? 10 rounds? isn't there a limit to 5?" followed by the explicit max_iterations 20->5 directive
