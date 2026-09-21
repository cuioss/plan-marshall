envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:00:19Z

component=plan-marshall:phase-3-outline
category=anti-pattern
bundle=plan-marshall

# Classify the design model from the deliverable's affected files, not from the mechanism it names

Deliverable 5's Design notes block classified `plan-marshall:manage-config` as
script-deterministic. That skill appears in NONE of the deliverable's affected
files. The deliverable actually edited three standards documents
(`plan-marshall/standards/effort-roles.md`,
`extension-api/standards/marshal-json-reference.md`,
`marshall-steward/standards/effort-menu.md`) plus `.plan/marshal.json`.

The consequence is twofold. No design-model classification was made for any of
the three surfaces the deliverable really touches, so the Step 9c check was never
performed against its real surface. And an implementation agent reading the block
would go extend `manage-config`'s scripts rather than edit the three documents.

Source record: Q-Gate finding `78c47c`, phase `3-outline`, resolution `accepted`.

## Solution

Derive the Design-notes classification from the deliverable's affected-files set,
one classification per touched surface. The skill that owns the WRITER mechanism a
deliverable invokes (`effort set --scope orchestrator.{surface}` here) is a
mechanism note, not a classification target — keep it as a note and classify the
files that change.

## Impact

The mis-scoped classification never misdirected an implementation agent on this
run: deliverable 5 landed against exactly the three standards docs plus the config
file. The remedy would edit an already-consumed outline artifact and change
nothing shipped, which is why the finding was accepted rather than fixed. The
generalizable half is the derivation rule.
