envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T15:41:27Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# create-pr Step 3.6 reads a manifest field enabled_bots that the composed manifest does not have

## What happened

`phase-6-finalize/workflow/create-pr.md` Step 3.6 reads a manifest field named `enabled_bots`. The composed execution manifest exposes **`required_bots`** and **`optional_bots`**. There is no `enabled_bots` key anywhere in the compose schema — the doc names a field that has never existed under that name.

## Why it matters for truthful signals

A doc-contract read of a non-existent key does not fail loudly. It resolves to nothing, and the step proceeds *as if no bots were configured* — which is behaviourally identical to a correct read of an empty configuration. The step cannot tell the two apart, and neither can anyone reading its output.

This lands on a surface the epic already knows is over-reporting. The standing rule is that enabled-bots-vs-operative drift is a recurring defect archetype and that a green `automatic-review` outcome is not evidence a bot saw the diff. A **bot-selection read that silently resolves empty** is upstream of that entire problem: it removes the run's ability to even state which reviewers were expected.

Circumstantial, not causal, but worth recording together: on this very run (#1057) `automatic-review` reported exactly one comment and `review-retrospective` compared exactly one reviewer, with neither CodeRabbit nor Sourcery present. The two observations sit on the same surface.

## Corrective rule

1. Fix the doc to name the two real fields (`required_bots`, `optional_bots`) and state the required-vs-optional distinction that governs gating.
2. **Then sweep every other manifest-field read across the finalize workflow docs against the live compose schema.** A doc naming a field the schema does not have is the same producer/consumer-mismatch archetype this epic has now hit repeatedly — and, per the epic's own standing correction, a reviewer's or an author's list of call sites is a SAMPLE, not an enumeration. The sweep must be population-derived from the compose schema's key set, not from reading the docs for names that "look wrong."
