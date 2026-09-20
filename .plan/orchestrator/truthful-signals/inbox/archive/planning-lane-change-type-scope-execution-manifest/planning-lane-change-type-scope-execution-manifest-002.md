envelope_version=1
sender_type=plan
sender_id=planning-lane-change-type-scope-execution-manifest
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T15:59:45Z

# A round loop closed at its iteration ceiling records the same done as a converged one

component: plan-marshall:phase-6-finalize
category: bug
confidence: high
source_plan: planning-lane-change-type-scope-execution-manifest
source_pr: 1399

## Context

`pre-submission-self-review` fired 19 times on this plan. Fifteen firings returned `loop_back` with target `6-finalize`; four returned `done`. `status.metadata.loop_back_iteration` reached `17` against the configured `max_iterations: 17`, so the ceiling was fully consumed.

The last closes were therefore not convergence. The step's own stored record spells them `outcome: done` — byte-identical to the record a genuinely converged round would write. The final `display_detail` reads `"delta round from 7c3565124: 3 contract-drift fixes landed; agent stalled before filing, findings NOT recorded"`, which is a partial round, and it is still stored under `done`.

The plan's own finding `28e6e8` names the distinction precisely, while fixing a different instance of it: an unresolved `{sha}` in Branch C created "a wedge only `max_iterations` breaks, **closing the step OUT OF BUDGET rather than converged, which is the exact distinction the round-loop termination rule exists to protect**". The rule exists; the ledger that would carry its outcome does not distinguish the two states.

## Root cause

`mark-step-done --outcome` offers `done` / `skipped` / `loop_back` / `failed`. There is no value, and no companion field, for *"the loop stopped because it ran out of iterations"*. Every terminal path — converged clean, converged with the last findings accepted, and budget-exhausted — lands on `done`.

Downstream every consumer that reads the finalize ledger (`refire-report`, `verdict-currency`, the dispatch audit's `dispatch_coverage`, and any cross-plan roll-up) counts a budget-exhausted close as a clean one. This is the same confident-signal-hides-a-caveat shape the `truthful-signals` epic exists to remove, occurring in the machinery that shipped a plan whose subject was exactly that shape.

## Proposed action

Record the termination *reason* alongside the outcome. Two shapes are available and neither needs a new outcome value:

1. A `termination_reason` fact on the step record (`converged` / `budget_exhausted` / `ceiling_hit_partial`), written by the dispatcher's loop-back continuation hook, which already knows `loop_back_iteration` against `max_iterations`.
2. Failing that, have the continuation hook record `--outcome failed` when it closes the loop on the ceiling rather than on a clean round — the `failed` value already means "ran cleanly and self-assessed not-clean", which is exactly what a ceiling-exhausted loop is.

Option 1 is preferable: it preserves the terminal-record semantics every other consumer depends on and adds the discriminator as a fact, mirroring how `create-pr` already stores `facts.pr_number`.

## Evidence

- aspect: logging_gap_analysis — 19 firings, 15 `loop_back`, `loop_back_iteration: 17` against `max_iterations: 17`
- aspect: log_analysis — 6-finalize dispatch ledger records 17 `returned_with_findings` rows over 61
- aspect: chat_history_analysis — the operator's only substantive turn in the last session is "why allways stopping?"
- finding `28e6e8` (this plan) — names the converged-vs-out-of-budget distinction as the one the round-loop termination rule protects
