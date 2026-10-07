envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:06:53Z

# Candidate lesson: script-failure cluster — plan-marshall:manage-execution-manifest:manage-execution-manifest

- source_signal: script_failure cluster (4 of 9 distinct notations)
- notation: `plan-marshall:manage-execution-manifest:manage-execution-manifest`
- marker: `[ERROR] ... script_failure ... Use a declared flag for ... step-params get: ['phase','plan-id','step-id']`

## What happened

`step-params get` was invoked with a flag outside its declared set of three. The call happened inside the review-retrospective finalize step, which needed a step's configured parameters.

## Candidate rule

Nested verbs (`step-params get`) carry their own flag set, distinct from both the top-level router and the noun. Read the declaration at the level that actually parses — the innermost subparser — rather than assuming flags declared on a sibling verb of the same noun apply.
