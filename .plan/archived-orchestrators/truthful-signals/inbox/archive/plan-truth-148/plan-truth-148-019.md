envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:00:29Z

# Candidate lesson: an enumeration named 2 of 3 states its own sibling definition covers

- source_signal: qgate / 6-finalize
- record_id: 619385
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:558
- resolution: fixed in the round-5 sweep (the omitted state was restored)

## What happened

Line 558 enumerated the non-findings-bearing verifier states that produce a Step-3b-filed finding as `refusal` and `unverified` — omitting `further_round_owed`, which line 493 of the same document defines identically broadly. A state with the same properties was silently outside the handling rule.

## Candidate rule

A hand-written enumeration of states drifts from the state definition it draws on. Derive the enumeration from the defining site, or at minimum publish the population size next to the list so a short list is visible as short.
