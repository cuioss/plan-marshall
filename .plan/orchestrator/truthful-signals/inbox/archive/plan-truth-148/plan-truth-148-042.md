envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:04:15Z

# Candidate lesson: a deliverable's declared pool was complete for its scope and left same-class drift outside it

- source_signal: qgate / 3-outline (scope_criterion_validator, under_coverage)
- record_id: f923e9
- component: solution-outline-deliverable-5
- file: marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md
- resolution: taken_into_account — superseded by an explicit scope decision at execute time (verdict e31a64)

## What happened

The drifted step-id token occurred in 37 files. The six phase-6-finalize files the deliverable named were confirmed exactly, so the declared pool was complete for the scope it stated. But at least two same-kind echoes survived outside it: `manage-status/SKILL.md` renders `step: automated-review` in worked examples and in the `step_record_missing` message, and `manage-execution-manifest/standards/manifest-schema.md` carries three more. These render a step row for an id the live population does not carry — the same defect class the deliverable existed to close.

## Candidate rule

A scope declared by DIRECTORY rather than by DEFECT CLASS leaves same-class instances live. When the finding is "this identity no longer exists", the natural scope is the identity's occurrence set; narrowing to one skill is legitimate only if the remainder is recorded as an owed follow-up rather than as out-of-scope-and-forgotten.
