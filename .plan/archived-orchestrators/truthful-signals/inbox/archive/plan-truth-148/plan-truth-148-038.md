envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:03:10Z

# Candidate lesson: the stop question must be an ADDITIONAL gate, not a replacement for three preconditions

- source_signal: qgate / 5-execute (D1 gate verdict)
- record_id: c67958
- component: plan-marshall:phase-6-finalize
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md
- resolution: taken_into_account — CONFIRMED; drove the stop-question gate while preserving all three named preconditions

## What happened

Branch A was selected by the bare predicate "findings list is empty" — the author's own reading of the list it had just produced. Three preconditions had to survive as conjuncts rather than be replaced: the full-surface precondition (forbidding a `done` recorded off a delta-scoped clean result), the zero-observation substitution, and the zero-generator carve-out. Separately re-verified: `--force` is present on every terminal branch that can overwrite a differing stored outcome, in BOTH directions (loop_back to done AND done to loop_back).

## Candidate rule

When adding a gate to a close decision, enumerate the existing preconditions and state explicitly that the new gate is conjunctive. A new gate written as the selector silently retires the guards it sits next to — and a document that describes the new gate without them reads as a complete statement of the closing rule.
