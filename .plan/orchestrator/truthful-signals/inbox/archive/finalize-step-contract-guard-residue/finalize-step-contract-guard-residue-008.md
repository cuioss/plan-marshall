envelope_version=1
sender_type=plan
sender_id=finalize-step-contract-guard-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T10:23:42Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=medium
source_plan=finalize-step-contract-guard-residue

# Reduce the operator prodding that dominates finalize interaction

## Context

The session transcript reduces to 16 operator turns out of 1609 raw turns, plus 5 gate decisions recovered from the tool-result channel.

Of those 16 operator turns:

- 1 is the launch command
- 1 is a harness-injected "previous response failed to produce a valid tool call. Please retry."
- **14 carry no instruction at all** — 5 bare `retry`, 4 `continue` variants (including one typo, `contniue`), 3 `why did you stop?`, and 2 explicit do-not-stop directives (`continue with finalize without further stops`, `continue without stopping`)

So the operator supplied direction 5 times, through the gate channel, and supplied **momentum 14 times**. 87.5 pct of operator turns exist only to restart a stalled run.

The prods cluster in finalize, which independently shows: 3h47m worked duration, 2,635,188 dispatched tokens (48 pct of the plan), 23 manifest steps, and `pre-submission-self-review` firing 8 times with 7 prior `failed` outcomes.

## Root cause

Not established from the available evidence, and this proposal deliberately stops short of asserting one. The correlation between the prod cluster and the 8 self-review firings is strong but the transcript reduction keeps only operator turns — the assistant-side turns that would show *why* each stall occurred were dropped (1593 of 1609). Candidate explanations that the evidence does not separate: dispatch returns that ended without advancing the step, review rounds awaiting an input the leaf could not obtain, and harness-level cancellations.

## Proposed action

First, measure it. The dispatch-boundary ledger already distinguishes productive from unproductive terminations, and this plan's finalize rows show 7 `step_complete`, 2 `returned_with_findings` and 1 `error` — no `harness_cancellation` and no `blocked_*`. That accounts for terminations but not for the gaps that prompted `why did you stop?`, so the instrumentation does not yet cover the observed failure.

Concretely: emit a work-log line whenever the finalize loop yields control without a step transition, carrying the reason. That converts "why did you stop?" from a question the operator has to ask into a recorded fact, and gives a subsequent retrospective the population it needs to attribute the stalls.

Only then consider a behavioural change — an auto-continue policy built on an unmeasured cause would be a guess.

## Evidence

- aspect: chat_history_analysis — `operator_turn_count: 16`, `prod_only_turns: 14`, `prod_share_of_operator_turns: 0.875`
- aspect: chat_history_analysis — prod breakdown: retry 5, continue variants 4, why-did-you-stop 3, explicit do-not-stop 2
- status.json — `pre-submission-self-review.firing_count: 8` with 7 prior `failed` rows
- aspect: plan_efficiency — 6-finalize worked 3h47m, 2,635,188 dispatched tokens, `max_phase_token_share: 0.48`
- aspect: logging_gap_analysis — finalize terminations: 7 step_complete, 2 returned_with_findings, 1 error, 0 harness_cancellation
