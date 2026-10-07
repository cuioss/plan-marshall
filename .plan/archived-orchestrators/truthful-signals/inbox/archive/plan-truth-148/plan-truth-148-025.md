envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:01:40Z

# Candidate lesson: the replacement pointer aimed at a section that did not carry the authority

- source_signal: qgate / 6-finalize
- record_id: c5d002
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md:145
- resolution: fixed — re-pointed at SKILL.md "Step Types" and the ext-point lane/order contract

## What happened

The round-7 fix replaced a hand-maintained order list with a pointer at SKILL.md's "Dispatched workflows vs inline steps" section — but that section covers only the dispatched/inline classification and says nothing about step ORDER. The pointer was correct in form and wrong in target.

## Candidate rule

Deletion-plus-pointer only discharges the defect when the pointer's target actually carries the fact. Verify the target section states the claim before landing the pointer; an unverified pointer is a dangling reference dressed as a fix, and it reads as resolved to every subsequent reviewer.
