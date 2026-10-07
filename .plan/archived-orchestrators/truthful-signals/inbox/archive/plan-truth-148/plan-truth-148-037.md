envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:03:07Z

# Candidate lesson: the party that produced the findings list was the party whose reading of it closed the step

- source_signal: qgate / 5-execute (D1 gate verdict)
- record_id: 0814ba
- component: plan-marshall:phase-6-finalize
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md
- resolution: taken_into_account — CONFIRMED; selected the reachable branch for the independence split

## What happened

At the pre-change HEAD author and verifier were the same party: whoever produced the findings list (dispatched or inline per the Step 1b gate) was also whoever's reading of that list selected Step 4's branch. No second role existed anywhere in the step. Two carried constraints had to survive the split — the shared return-TOON shape across both branches, and four out-of-scope properties (delta/full scoping, the cohort sweep, `structural_limit`, and the converged-versus-out-of-budget distinction).

## Candidate rule

A self-review that decides its own close is not a gate. When splitting author from verifier, express the independence as ROLE SEPARATION ACROSS THE DISPATCH BOUNDARY, not as new judgment inside the deterministic surfacer — the surfacer is a read-only script-executor and adding judgment there recreates the single-party arrangement inside a component that cannot be held to it.
