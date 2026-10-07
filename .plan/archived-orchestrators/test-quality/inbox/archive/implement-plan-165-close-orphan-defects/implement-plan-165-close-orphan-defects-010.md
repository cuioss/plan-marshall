envelope_version=1
sender_type=plan
sender_id=implement-plan-165-close-orphan-defects
epic=test-quality
kind=candidate-lesson
created=2026-09-13T11:23:53Z

component=plan-marshall:phase-3-outline
category=bug

# A deliverable's declared module is derived from the architecture inventory, never chosen

Deliverable 2 declared `module: default` in its Metadata block while both of its
affected paths live under `test/plan-marshall/manage-providers/`, which
`architecture which-module --path ...` attributes to module `plan-marshall`. The
declaration was wrong three ways at once, and each disagreement was independently
checkable:

1. Against the **architecture inventory** — the authoritative attribution for the
   paths the deliverable names.
2. Against a **peer deliverable over the same directory** — deliverable 3 declared
   `module: plan-marshall` for `test_configure.py`, a sibling in the very same
   directory. Two deliverables claimed different modules for one directory.
3. Against the deliverable's **own verification command**, `coverage
   plan-marshall`, which named the module the Metadata block denied.

## The failure shape

`default` is the plausible-looking value: it is a real module, it is the
cross-cutting home, and it never trips a "module not found" error. So a Metadata
block filled in by judgement rather than by lookup lands on it silently, and the
inconsistency only surfaces when something downstream reads the field.

## Solution

Fill each deliverable's `module` from `architecture which-module --path P` over
that deliverable's own affected paths — a lookup, not a judgement. Then audit the
Metadata blocks **as a peer set** rather than one at a time: deliverables whose
paths share a directory must declare the same module, and a deliverable's declared
module must match the module its verification command scopes to. Reserve `default`
for genuinely cross-cutting, root-level work — not as the value for "I did not
look it up".

## Impact

The wrong module misroutes verification scoping and module-attributed reporting.
The peer-set audit is the part most easily skipped: this run found the defect in
one of four blocks and confirmed the other three were already correct, which is
only knowable by checking all four.
