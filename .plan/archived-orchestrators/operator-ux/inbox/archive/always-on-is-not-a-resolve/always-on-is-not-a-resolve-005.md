envelope_version=1
sender_type=plan
sender_id=always-on-is-not-a-resolve
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T19:22:17Z

component=plan-marshall:phase-6-finalize
category=improvement
bundle=plan-marshall
confidence=high

# Stop HEAD-bound step invalidation re-firing the whole head-bound set per finalize commit

## Context

`always-on-is-not-a-resolve` is a `single_module` / `bug_fix` plan that mutated
five files across two deliverables and three tasks. It recorded 3,531,482 tokens,
crossing the `single_module + bug_fix` **error** anchor (1.3M) by 2.7x, and
1h53m of wall clock against a 90-minute error anchor. `6-finalize` alone
accounts for 2,063,981 of those tokens — 58% — against 1,467,501 for phases 1
through 5 combined. Both figures are floors: `6-finalize` never closed, so the
totals are lower bounds.

The mechanism is visible in `status.metadata.phase_steps`. Only one loop-back
was recorded (`loop_back_iteration: 1`), but four distinct
`head_at_completion` values appear across the finalize steps — `43ed295b`,
`8827a7f2`, `487b0cc4`, `87782159` — i.e. HEAD moved four times *inside*
finalize, and each move invalidated the head-bound steps that had already
passed. Resulting firing counts:

| Step | firings |
|---|---:|
| pre-push-quality-gate | 4 |
| finalize-step-simplify | 4 |
| automatic-review | 3 |
| project:finalize-step-lessons-housekeeping | 2 |
| project:finalize-step-plugin-doctor | 2 |
| pre-submission-self-review | 2 |
| ci-verify | 2 |

That is 12 step firings beyond first-fire — the quality gate ran four times for
three implementation tasks.

## Root cause

Head-bound steps are invalidated by *any* HEAD movement, including movement that
finalize itself caused. A step that commits (simplify, era-stamp-fill, a
triage fix) moves HEAD and thereby re-arms every step already validated at the
prior HEAD, whether or not that step's own inputs were touched. The invalidation
predicate is HEAD identity, not footprint overlap, so self-inflicted movement is
indistinguishable from an upstream rebase.

## Proposed action

Narrow the invalidation predicate from "HEAD changed" to "HEAD changed in a way
this step's inputs can see". The realized diff between `head_at_completion` and
the new HEAD is already computable, and each step's relevant surface is already
declared (the quality gate's bundle scope, simplify's changed-file set,
plugin-doctor's scoped paths). A step whose declared surface is disjoint from
the intervening diff can carry its prior pass forward rather than re-firing.

If narrowing the predicate is too large a change, a cheaper first cut is to
order the committing steps ahead of the head-bound validating steps so finalize
moves HEAD once, before the gates, instead of interleaving.

## Evidence

- aspect: plan_efficiency — `[BUDGET]` error anchor tripped on both tokens (3.53M vs 1.3M) and wall clock (1h53m vs 90 min); `max_phase_token_share=0.58`, `dominant_phase=6-finalize=2063981`
- aspect: logging_gap_analysis — 13 dispatch-boundary rows in `6-finalize` against 2 in `5-execute`; one terminated `error` burning 146,764 tokens for zero detection
- aspect: invariant_summary — `main_sha` drift 4-plan to 5-execute, and four distinct `head_at_completion` values inside finalize
