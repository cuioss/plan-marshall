envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:01:54Z

# Candidate lesson: the declared frontmatter surface and the surface the code reads had diverged

- source_signal: qgate / 5-execute (D1 gate verdict)
- record_id: 803c50
- component: plan-marshall:extension-api
- file: marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md
- resolution: taken_into_account — this verdict drove the deliverable's table-side reconciliation

## What happened

The implementor record the code builds carries `canonicals`, `source`, `path` and conditional `verification_profile` — none of which had a row in the Implementor-Frontmatter table, while `canonicals` is visibly emitted as a column by the live CLI. The gap was TABLE-side, not docstring-side. The verdict also amended its own premise: the docstring's exclusion clause said "every field the table marks Conditional are NOT on this record", but three OPTIONAL rows were equally absent, so the clause under-described its own exclusion.

## Candidate rule

Reconcile a declared surface against a read surface in BOTH directions and record which side is authoritative before editing either. An exclusion clause phrased over one marking class (Conditional) silently misdescribes the members of the adjacent class (Optional) with the same property.
