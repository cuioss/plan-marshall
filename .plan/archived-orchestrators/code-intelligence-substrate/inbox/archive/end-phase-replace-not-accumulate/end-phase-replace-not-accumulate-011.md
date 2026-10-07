envelope_version=1
sender_type=plan
sender_id=end-phase-replace-not-accumulate
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T17:24:24Z

component=plan-marshall:manage-execution-manifest
category=bug
created=2026-07-29

# compose records a reasoned omission whose condition is structurally always true, then contradicts it 0 seconds later

Two consecutive `decision.log` entries from `compose`, same timestamp:

```
[13:03:12Z] [c409ae] pre-push-quality-gate omitted — plan footprint is empty — no changed files to build
[13:03:12Z] [660085] ceremony_finalize selection — finalize.qgate=always, added pre-push-quality-gate to phase_6.steps
```

The step is omitted for a stated reason and re-added in the same second. And `pre-push-quality-gate` did run in 6-finalize, greenly.

## Why the predicate is vacuous, not merely wrong

`compose` runs in **4-plan**. Execute has not happened. No task has mutated a file. The plan footprint is therefore empty **every single time this predicate is evaluated, for every plan** — it is not a condition that sometimes holds, it is a structural constant of when compose runs. A guard that can only ever evaluate one way is not a guard; it is an unconditional omission wearing a rationale.

This is the vacuous-guard archetype the plan-marshall corpus has now hit repeatedly, and it has the specific aggravating feature that the decision log presents it as evidence-based reasoning ("plan footprint is empty — no changed files to build") when the evidence could not have been otherwise.

## Impact

Two costs, one immediate and one latent.

Immediate: the decision log is the audit surface for manifest composition, and it now contains a reasoned-looking claim that carries no information. Anyone auditing why a step was dropped will read `c409ae` as a real footprint-based decision.

Latent, and worse: because `ceremony_finalize` happened to re-add the step (`finalize.qgate=always`), the vacuous omission was harmless **in this configuration only**. Under a configuration where `finalize.qgate` is not `always`, the same vacuous predicate would silently drop the pre-push quality gate from every plan's manifest, and the decision log would explain the drop with a rationale that is always true. A gate that disappears for a reason that is never false is a false-green generator.

## Suggested corrective action

1. Remove the empty-footprint predicate from `compose`, or move the decision to a point in the lifecycle where the footprint is actually knowable (end of 5-execute, where `check-manifest-consistency` already evaluates footprint-dependent rules).
2. If the intent was "skip the gate for a plan that will change nothing", derive that from the plan's declared deliverable footprint (`solution_outline.md` Affected files, which IS available at compose time) rather than from the realized footprint, which is not.
3. Add a test that asserts no compose-time predicate reads the realized footprint. More generally: a predicate evaluated at a fixed lifecycle point should be checked for whether its condition can vary at that point — a guard whose input is constant at evaluation time is a defect regardless of which way it evaluates.
4. Sweep the other compose predicates for the same shape. `routing-decisions` reported `mis_prune:sonar-roundtrip` as `skip` because the step was removed by `posture_cutoff` before its prune predicate was ever evaluated, which is a second instance of a decision recorded without its predicate having run.
