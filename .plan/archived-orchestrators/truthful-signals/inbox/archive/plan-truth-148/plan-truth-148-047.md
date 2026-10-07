envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:04:29Z

# Candidate lesson: a deliverable's own text committed to files its affected_files did not list

- source_signal: qgate / 4-plan (scope_criterion_validator, under_coverage)
- record_id: 75009d
- component: plan-marshall:phase-6-finalize
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md
- resolution: taken_into_account — duplicate of outline finding f923e9 at the plan phase, resolved the same way at execute time

## What happened

Deliverable 5's Change-per-file text named a four-file candidate pool beyond its two `affected_files`, and a sweep confirmed all four carried the drifted token. None appeared in `affected_files`, not even as a survey-scope read entry, although the deliverable's own text committed to classifying and possibly correcting each.

Note the shape: the SAME under-coverage was raised at outline (f923e9) and again at plan (75009d), and both were deferred to execute time rather than closed at either gate.

## Candidate rule

`affected_files` must be the union of every file the deliverable's own prose commits to touching or surveying — the Files-to-survey / Files-expected-to-mutate pair exists for exactly this. And when the same finding recurs at a second gate, that recurrence is evidence the first gate's disposition did not hold, not a duplicate to dismiss: every `affected_files`-derived downstream computation (footprint, scoping, finalize step selection) under-scopes for as long as it stands.
