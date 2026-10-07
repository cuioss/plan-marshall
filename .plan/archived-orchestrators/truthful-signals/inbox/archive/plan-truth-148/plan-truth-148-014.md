envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:59:24Z

# Candidate lesson: the document's own summary line still selected on the retired predicate

- source_signal: qgate / 6-finalize
- record_id: 76cabb
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:31
- resolution: fixed in the round-4 sweep by deletion/pointer

## What happened

Line 31 — the document's own opening summary — still said "a clean run records outcome=done; a non-empty findings list records outcome=loop_back", selecting the outcome from the findings list alone and contradicting the new precondition requiring the verifier's acceptance and stop answer.

## Candidate rule

The opening summary of a workflow doc is a restatement of its own rule and drifts the moment the rule changes. When a selector changes, the summary paragraph is the first place to sweep, and the durable fix is to make the summary point at the rule rather than paraphrase it.
