envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:06:48Z

# Candidate lesson: script-failure cluster — plan-marshall:manage-solution-outline:manage-solution-outline

- source_signal: script_failure cluster (2 of 9 distinct notations)
- notation: `plan-marshall:manage-solution-outline:manage-solution-outline`
- markers: three `[ERROR] ... script_failure` lines, in phase-5-execute and again in the retrospective step

## What happened

Two failure shapes, the first recurring across two different phases hours apart:

1. `Use ... list-deliverables — registered: ['exists','get-deliverable','get-field','get-module-context','list-deliverables','read','resolve-path','update','validate','write']` — a paraphrased verb was invented in place of the registered one. This fired at 19:01 during execute AND again at 20:37 during the retrospective, which means the correction did not propagate between envelopes.
2. `Use a declared flag for ... get-deliverable: ['deliverable-number','plan-id']` — an undeclared flag on an otherwise correct verb.

## Candidate rule

Verb-paraphrase is the canonical argparse-rejection signature and it RECURS ACROSS ENVELOPES: a correction learned in one dispatch is not carried into the next, so the same invented verb is re-attempted later in the same plan. The durable remedy is at the authoring layer — workflow prose that names a verb must name the registered spelling verbatim, because prose is the only thing both envelopes read.
