envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:00:23Z

# Candidate lesson: prose named acceptance alone as what closes the step

- source_signal: qgate / 6-finalize
- record_id: 31e1f5
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:80
- resolution: fixed in the round-5 self-seeding sweep

## What happened

"Step 4 reads an acceptance that neither role could grant itself" named acceptance as the sole closing input, contradicting the precondition that Branch A needs BOTH the acceptance and the `may_close` answer.

## Candidate rule

When a precondition goes from one conjunct to two, every prose sentence that names the old single condition becomes a contradiction. Enumerate those sentences by content sweep of the condition's name, not by reading the sections you happened to edit.
