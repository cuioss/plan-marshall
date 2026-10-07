envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:01:42Z

# Candidate lesson: records_facts declared the new fields and omitted the one the ext-point requires

- source_signal: qgate / 6-finalize
- record_id: 68c246
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:12
- resolution: fixed in the round-9 sweep — `work_performed` declared and wired true/false per branch

## What happened

`records_facts` was declared with `acceptance` and `may_close` but omitted `work_performed`, which `ext-point-finalize-step.md` requires whenever a `done` branch is reachable without the step's characteristic work — which the zero-generator fallback is.

## Candidate rule

When a step first declares `records_facts`, read the ext-point's own conditional obligations for that key rather than declaring only the fields the current change introduced. The declaration is a contract with the extension point, not a description of this commit's additions.
