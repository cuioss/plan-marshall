envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-08T10:39:05Z

component=plan-marshall:phase-6-finalize
category=bug

Relayed from Token-Sheriff PLAN-12 (PR #720 / `e52ec470`). Two step-selection defects from one run, bundled because they share a shape: **a step was dropped by a mechanism whose own stated rationale did not apply to the path it was dropped on.** The bundling is the relaying orchestrator's judgement — split them if you disagree.

## A — Tier-1 recipe-match suppresses q-gate-validation where its rationale does not hold

# Candidate lesson: Tier-1 recipe-match suppresses q-gate-validation on a path where its own rationale does not hold

**Component**: `plan-marshall:phase-3-outline` / `plan-marshall:phase-1-init` (Tier-1 recipe-match routing)
**Signal class**: Q-Gate / routing observation from this run
**Landed in**: PR #720, squash commit `e52ec470`.

## Observation

The Tier-1 recipe-match routed shortcut suppressed `q-gate-validation` at `3-outline`. The
stated justification for that suppression is:

> the recipe outline shape is already determined by the matched transformation

That rationale requires the outline to actually have been produced by the recipe. On the
Tier-1 **auto-routed** path it was not:

- Tier-1 auto-routing sets `status.metadata.recipe_key`.
- It does **not** set `plan_source=recipe`.
- `phase-3-outline` Step 3 branches on `plan_source`, so with `recipe_key` set but
  `plan_source` unset it took the full Complex Track and authored a **bespoke** outline.

So the outline whose validation was skipped was not recipe-shaped at all. The suppression
fired on its trigger (`recipe_key` present) while its precondition (recipe-authored outline)
was false.

## Why this matters

This is a silent-weakening shape, not a loud failure: the run proceeds, the outline looks
normal, and nothing anywhere states that a validation was skipped on a false premise. The
failure is only visible by reading the two routing predicates side by side.

## Suggested direction (for orchestrator judgement)

The suppression predicate and the shortcut's rationale should read the same fact. Either
auto-routing sets `plan_source=recipe` when it sets `recipe_key`, or the suppression keys on
the fact Step 3 actually branched on rather than on `recipe_key` presence.

---

## B — the scope gate dropped a step whose own step_params forbid that drop

# Candidate lesson: scope gate dropped a step whose own step_params forbid that drop, removing the basis of an operator decision

**Component**: `plan-marshall:manage-execution-manifest` (phase-4 manifest composer)
**Signal class**: Q-Gate / manifest-composition observation from this run
**Landed in**: PR #720, squash commit `e52ec470`.

## Observation

The phase-4 manifest composer dropped `pre-submission-self-review` with reason
`scope_gated_finalize_dropped` (`scope_estimate=surgical`), although:

1. That step's own `step_params` carry `drop_review_on_scope_gate: false` — an explicit
   per-step opt-out of exactly this gate.
2. The operator had explicitly selected the `standard` posture, and the observable difference
   `standard` makes over `minimal` in this run is that it adds that step. The step was
   therefore the stated basis of the operator's choice.

The drop was silent: the manifest recorded the reason, but nothing surfaced that the operator's
chosen posture had been reduced to the posture they had not chosen.

## Two distinct defects in one observation

- **Precedence**: a per-step `drop_review_on_scope_gate: false` did not outrank the scope gate.
  A parameter whose only purpose is to refuse a gate must outrank that gate or it means nothing.
- **Consent**: an operator posture decision was invalidated after the fact without a report.
  Where a scope gate removes what the operator's selection was *for*, the removal is a decision
  the operator needs to see, not a composition detail.

## Suggested direction (for orchestrator judgement)

Make the scope gate consult `drop_review_on_scope_gate` before dropping, and surface any drop
that reduces an operator-selected posture to its next-lower equivalent.
