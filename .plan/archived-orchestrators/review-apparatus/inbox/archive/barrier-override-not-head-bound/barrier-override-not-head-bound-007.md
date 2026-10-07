envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T11:43:54Z

component=plan-marshall:phase-6-finalize
category=bug
title=A simplify pass is a code mutation that can regress typing - only the HEAD-dependent gate re-fire caught a dropped mypy annotation

# A simplify pass silently dropped a mypy annotation; the head-dependent gate re-fire was the only thing that caught it

## What happened

During plan `barrier-override-not-head-bound`'s finalize settle band, the
`finalize-step-simplify` pass (recorded as *"Simplify: 4 edits, 3 findings"*) **silently
dropped a mypy annotation**. The simplify step reported success; nothing in its own output
indicated a typing regression.

It was caught **only** because `pre-push-quality-gate` declares `head_dependent: true`: the
simplify step's edits were committed by the dispatcher's commit instrumentation, which
advanced HEAD past the SHA the quality gate had recorded in `head_at_completion`. The
re-entry check observed `head_at_completion != live HEAD`, RE-FIRED the gate, and the gate
went red. Final record: *"re-fired after settle commits — whole-tree quality-gate + verify
plan-marshall green"*.

Without the HEAD-comparison the stale `done` record would have been trusted, the gate would
have been SKIPped, and a typing regression would have shipped behind a green finalize.

## Why it matters

1. **A "quality only, no behaviour change" pass is still a code mutation.** `simplify` is
   framed as a cleanup — reuse, altitude, efficiency — which invites treating its output as
   safe by construction. It edits real source, and an annotation is exactly the kind of
   detail an altitude-focused rewrite drops without noticing.
2. **The settle band's ordering is load-bearing, not incidental.** The gate at `order: 5`
   runs BEFORE the mutating steps at higher orders. Its verdict is therefore always about a
   superseded tree by the time push happens — unless it re-fires. The head-dependence
   declaration is what converts an ordering accident into a guarantee.
3. **This is a positive datapoint for the head-dependence mechanism**, and worth recording as
   such: `head_dependent: true` + `head_at_completion` earned its keep on a real regression,
   not a hypothetical one. The general rule it encodes — *a head-dependent verdict is never
   left standing as green for a HEAD it was not computed against* — is now evidenced.

## Rule

1. **Any finalize step that edits source must be treated as capable of regressing every gate
   that ran before it.** Its `mutates_source: true` declaration is what arms the dispatcher's
   commit instrumentation and thereby the downstream re-fire; a source-editing step that omits
   the declaration silently disarms the protection.
2. **A step whose verdict would change if HEAD changed MUST declare `head_dependent: true`
   and persist `head_at_completion`.** A `done` record with no SHA was never anchored to a
   tree and must be reported UNVERIFIED, not trusted.
3. **Do not read a simplify/refactor pass's own success as evidence the tree still passes.**
   The pass reports what it changed, not what it broke. The gate re-run is the evidence.
4. **When adding a new settle-band step, check both facts explicitly** — does it mutate
   source, and is its own verdict head-dependent — rather than inferring either from its
   position in the roster or from the dispatched/inline split (head-dependence is orthogonal
   to that split).

## Scope note for the orchestrator

Concrete site: `finalize-step-simplify` + `pre-push-quality-gate` in `phase-6-finalize`.
Two candidate increments: (a) a mypy/type-annotation-preservation check inside the simplify
pass itself, so the regression is caught at the producing step rather than downstream; (b)
record this as the evidenced-in-production justification for the head-dependence mechanism.
Classification deferred to the orchestrator.
