envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:00:32Z

# Candidate lesson: a restatement of a return contract was narrower than the contract

- source_signal: qgate / 6-finalize
- record_id: 879aaa
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:82
- resolution: fixed in the round-6 sweep by narrowing the restatement to a pointer

## What happened

The "Author and verifier are different parties" section restated the verifier's return contract while omitting `may_close` and the rationale field — a narrower copy of a contract stated authoritatively one section away.

## Candidate rule

Duplicate prose is not merely redundant; a duplicate that is narrower than its source is an active misstatement of the contract. The only stable remedy is a pointer. This is the same defect shape that this plan's other same-document findings share, and the fix that terminated the loop in every case was deletion-plus-pointer, never a corrected second copy.
