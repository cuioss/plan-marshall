envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:59:10Z

# Candidate lesson: a retired selector survived in the section a caller reads first

- source_signal: qgate / 6-finalize
- record_id: 86147d
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:385
- resolution: fixed (sentence deleted, not restated; verified by a 5462-file content sweep returning count 0)

## What happened

A change retired "empty findings list closes the step" as the branch selector and replaced it with the verifier's stop answer. The retired rule survived verbatim in the `## Dispatched-envelope output` section — exactly the section a caller implementing the return contract reads first — so a reader following it would mark `done` on an empty findings list with no verifier involved, reinstating the arrangement the whole change existed to remove.

## Candidate rule

When a change retires a selector, sweep the document's CALLER-FACING sections first, not only the section that defines the rule. And fix by DELETION, letting the one authoritative statement stand, rather than by authoring a second corrected copy that can drift again.
