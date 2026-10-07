envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:55:09Z

component=plan-marshall:phase-2-refine
category=bug
proposed_title=LIVE DIVERGENCE (undetermined): refine logged scope=surgical, references.json held single_module

# LIVE DIVERGENCE (undetermined): refine logged `scope=surgical`, `references.json` held `single_module`

## Status

**Observed in-flight during `lane-router-reads-the-wrong-body`, deliberately NOT fixed.** Mechanism undetermined. Route it — there are two candidate causes and they need different fixes.

## The observation

Within one run of this plan:

- `phase-2-refine` emitted the work-log line: `Scope: surgical - Modules: 1, Files: 3`
- `references.json` at the same point held `scope_estimate: single_module`

Two different values for the same field inside one plan.

## The two candidate mechanisms

**(a) A dropped/unchecked persist in refine.** Refine computed `surgical`, called the persist, and the write never landed — or landed and its result was never checked. This is the **PLAN-86 unchecked-persist archetype** (PLAN-86 swept and found 10 persist sites, two of them 100% broken, and all four producer-mismatch emitters were themselves unchecked persists).

**(b) `phase-3-outline` overwrote refine's value.** A later writer clobbered the earlier, more-informed estimate.

## The evidence that discriminates them (partially)

The documented refinement direction is a **DOWNGRADE**: refinement is supposed to move an estimate toward *narrower* scope as confidence rises. `surgical` → `single_module` is a **widening**, i.e. the wrong direction for a legitimate refinement. That leans toward **(a) a dropped persist** — the observed value looks like a stale/default that survived because the real write never landed — rather than an intentional outline-side re-estimate.

It is not conclusive. Both need checking.

## Why it matters

`scope_estimate` is the input to lane routing. A silently-lost refine value means the router runs on a *less-informed* estimate than the system actually computed — and there is no signal anywhere that the better value existed and was lost. Confident output, hidden caveat.

## The rule (candidate)

- **Every `scope_estimate` persist must be result-checked.** Sweep the writer set (four known writers — see the sibling vocabulary-divergence message) and confirm each checks its persist return, per PLAN-86's finding that this class is systematically unchecked.
- **A widening refinement must be refused or flagged.** If refine/outline moves `scope_estimate` toward a broader class, that is either a bug or a decision that deserves an explicit log line with a reason. Silent widening should not be representable.

## Reproduction pointer

`.plan/local/plans/lane-router-reads-the-wrong-body/logs/work.log` (the `Scope: surgical - Modules: 1, Files: 3` line) against the same plan's `references.json`.
