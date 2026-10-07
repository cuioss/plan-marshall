envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T04:55:29Z

component=execution-context
category=bug
created=2026-07-29

# A dispatched leaf correctly refused rather than editing from an unproven seed

`phase-5-execute` returned `blocked` (`tooling_capability_gap`) rather than
editing from the unproven 14-file seed, because Grep/Glob were not granted in
its dispatched envelope. That refusal was RIGHT and prevented a third recurrence
of the field-name-sweep-misses-caller-graph defect. But it also exposes a real
capability gap: `execution-context`'s frontmatter declares Grep/Glob while the
harness narrowed the granted set below the declaration, so a leaf that needs a
broad content sweep has no sanctioned fallback except returning the gap to the
orchestrator.

## Impact

A leaf's declared tool surface (frontmatter) and its actually-granted runtime
surface can diverge. When they do, refusing to proceed on an unproven seed and
returning `blocked`/`tooling_capability_gap` is the correct behavior — never
silently degrade to spot-checks or proceed on an unverified sweep.
