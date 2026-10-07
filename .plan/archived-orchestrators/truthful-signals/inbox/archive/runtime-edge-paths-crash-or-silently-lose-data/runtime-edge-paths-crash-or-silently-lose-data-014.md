envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:35:53Z

component=plan-marshall:phase-3-outline
category=anti-pattern
confidence=high
source_plan=runtime-edge-paths-crash-or-silently-lose-data
source_finding=eb608d
source_signal=execute_insight

# A read-only review that softens a severity by reasoning about a call site must execute it first

## The archetype

Two independent read-only reviews — phase-2-refine and phase-3-outline — each recorded the same
softening correction to a staged defect, and the correction was **wrong**. Executing the pre-fix
source refuted both.

This is the shape: *a review reasons about what a defect does at its call site, concludes it fails
safe, and writes that conclusion into the plan narrative as a correction to the original claim.*
The conclusion is presented as a refinement of the evidence when it is in fact a substitution for
it — an argument standing where an execution should be.

## What happened concretely

Staged defect **R10**: `rel = Path(module_rel).as_posix().lstrip('./')` collapses a repo-root module
(`'.'`) to `''`. Both review phases recorded that the collapsed empty string "currently fails SAFE
to `False` at its one call site", so the fragility was real but not presently mis-classifying.

The empirical pre-fix run refuted it. With `_cmd_manage.py` reverted to pre-fix:

```
assert _is_bundle('../marketplace/bundles/foo') is False
E   AssertionError: assert True is False
```

and `_is_bundle('marketplace/bundles/../../etc/foo')` likewise returned `True`. The helper
**mis-classifies traversal paths as in-bundle — it fails OPEN, not safe.**

The same round showed the `opencode/emitter.py` and `plugin_discover.py` traversal references were
actually being resolved onto decoy in-tree paths. So the flattening hazard was demonstrated, not
hypothesised.

## Why two independent reviews made the same error

They were not independent in the way that matters. Both read the same source and applied the same
method — trace the value to its consumer, judge the consumer's behaviour. Neither ran it. Two
passes of the same fallible method agreeing is one observation, not two, and the agreement made the
softening look corroborated.

This is the mirror image of the pre-fix-verification gap the plan's D8 deliverable closed: D8
required every regression test to be *observed failing* against pre-fix source rather than asserted
to fail. Had the same standard been applied to the review phases' softening claims, the error would
have been caught at outline instead of at execute.

## Proposed action

Make the standard symmetric. A read-only phase may **raise** a severity on argument alone, but
**lowering** one — declaring an observed defect benign, unreachable, or fail-safe at its call site —
is a claim about runtime behaviour and should carry one of:

- an executed probe against the current source, or
- an explicit `UNVERIFIED-SOFTENING` label that keeps the original severity in force for planning
  purposes until execute resolves it.

Concretely, in `phase-3-outline`'s claim-labelling: a correction that weakens a staged claim should
be labelled with the same rigour a staged claim itself requires, and "reasoned at the call site" is
not the same label as "re-verified at HEAD".

## Evidence

- finding `eb608d` (this plan), type insight, component `plan-marshall:manage-architecture`
- pre-fix test observations: `test_is_marketplace_bundle_module_refuses_parent_traversal` and
  `..._refuses_embedded_traversal` both failed `assert True is False` against reverted source
- the plan spec's own guidance already anticipated the general failure mode: "verify by symbol,
  never by line", and "population-derive the sweep"
- the finding text itself nominates this as "the archetype worth carrying to the epic"

## Related recurrence

Adjacent to the epic's existing `vacuous-authority` and `volume-read-as-coverage` archetypes: all
three are cases where the *form* of verification was present and the *act* was not.
