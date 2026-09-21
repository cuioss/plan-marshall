envelope_version=1
sender_type=plan
sender_id=git-artifact-scanning-and-destructive-recovery
epic=truthful-signals
kind=candidate-lesson
created=2026-08-31T08:03:28Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-08-31
bundle=plan-marshall
confidence=high
source_plan=git-artifact-scanning-and-destructive-recovery

# Persist the unattended directive as run state so step boundaries stop re-asking

## Context

The operator gave a standing directive early in this run and then had to re-assert it nine times.

The directive, in the operator's own words: "continue as defined to the end of finalize. DO only stop on issue. If you run into the coderabbit limit, wait the remaining time for the window to be resetted, Do the wait up to 5 times (parallel plans running)", followed by "Reason you run now unattended until tomorrow morning". The operator also had to say "consider `plan_without_asking`: true for this plan" as prose rather than having a persisted flag read from state.

Of the seventeen operator turns in this session, **nine (53%) were pure continuation prompts** carrying no new information:

- "why did you stop?"
- "do continue"
- "continue. GO thorugh finalize without stopping"
- "why did you stop?"
- "did you stop again? Runt finalize until done"
- "why did you stop? continue with finalize to the end"
- "igenore the lock, continue with finalize"
- "continue finalize to the end"
- "continue with finalize without further stopping"

Only three turns were substantive instructions and three were quality challenges. The remaining two were the launch.

## Root cause

The directive lived in the orchestrator's conversational context, not in run state. A finalize phase spanning roughly fourteen hours of wall clock, twenty-three steps, five `automatic-review` firings and two loop-back iterations crosses many context boundaries; a prose instruction held only in context is exactly the thing a compaction drops. Every drop cost a round trip — and on a 5.7M-token plan, a round trip is a context re-read.

This is the largest single recoverable operator cost in the run, and it is entirely mechanical.

## Proposed action

1. When the operator issues a run-scoped unattended directive, **persist it to `status.metadata` at the point it is given** — the same way `plan_without_asking`, `final_merge_without_asking` and the `merge_hold_*` budgets are already persisted — including its bounded parameters (here: "wait out the review window up to 5 times").
2. Have the finalize FOR loop consult that field at each step boundary rather than relying on in-context memory. A step that would otherwise return control to the operator checks the persisted directive first and, when it applies, logs a `[STATUS]` line recording that it proceeded under a standing directive rather than stopping.
3. When a step *does* stop under a persisted unattended directive, require it to name in `display_detail` the specific condition the directive did not cover. "Only stop on issue" is answerable; "I stopped" is not.

## Evidence

- aspect: chat_history_analysis — `operator_turn_taxonomy`: continuation_nag 9 of 17 (53%)
- aspect: plan_efficiency — 6-finalize consumed 2,756,653 tokens, 48% of the plan's total, and that figure is a floor
- Run facts: 23 finalize steps, 5 `automatic-review` firings, 3 `ci-verify` firings, 2 loop-back iterations of a permitted 5, roughly 14h wall clock in the phase
