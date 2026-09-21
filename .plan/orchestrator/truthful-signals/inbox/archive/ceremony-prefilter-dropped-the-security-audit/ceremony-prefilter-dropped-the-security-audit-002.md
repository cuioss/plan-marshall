envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T15:46:01Z

component=plan-marshall:phase-4-plan
category=bug
created=2026-07-29

# A correct read of the wrong scope: change_type is taken from the FIRST deliverable

`phase-4-plan` derives a plan's `change_type` from its **first deliverable**, then publishes that
value as if it described the whole plan. Every downstream gate that reads `change_type` therefore
reads a value whose scope is one deliverable, not the plan.

The failure mode is not a stale read — the value is freshly and correctly computed. It is a
**correct read of the wrong scope**. A plan that opens with a read-only discovery or analysis
deliverable reports `change_type: verification` however much production code its later deliverables
mutate. Nothing anywhere is inconsistent; every component is doing its job; the answer is wrong.

## Evidence

PLAN-112 was commissioned to fix exactly this class of defect in the finalize ceremony pre-filter,
and **reproduced it on itself**: its own phase-4 `execution.toon` carried
`security_audit_omitted=true` and dropped `finalize-step-security-audit` from its own finalize —
on a 47-file code change, under an operator-chosen *full* execution posture. Re-composing the
manifest against the fixed composer restored the step (23 → 24 steps).

## Solution

Two independent moves; the first is the root fix, the second is the containment that survives it.

1. **Derive a plan-level `change_type` from the union of deliverables, not from `deliverables[0]`.**
   The mutating-ness of a plan is a disjunction: if *any* deliverable mutates source, the plan
   mutates source. Taking the first element is a scope error dressed as a default.
2. **Never let a single-value scope proxy suppress a safety-class step.** A gate whose false branch
   removes a protective step must fail toward inclusion. PLAN-112's fix drops the `change_type` leg
   from the security gate entirely: it now drops only when the declared affected files AND the live
   footprint are **both** empty — two independent readings of the same underlying fact, both of
   which must agree before anything is removed.

## Impact

Applies to every consumer of `status.metadata.change_type` and to every ceremony gate that reads it.
PLAN-112 fixed exactly one such gate. The mis-scoped derivation itself is **still live**, and the
same root cause is still active for `finalize-step-simplify`'s `simplify_inactive` gate — lesson
`2026-07-16-20-001` was TRIMMED rather than removed for precisely that reason.

Generalization worth carrying: **when a summary field is derived from one member of a collection,
name the derivation in the field, or derive it from the whole collection.** A field called
`change_type` that means "the change type of the first deliverable" is a confident signal hiding
its own caveat.
