envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T20:22:07Z

# Candidate lesson: a deliverable's module field named one module while its files spanned two

Source: Q-Gate finding 7ab435 (phase 3-outline, resolved: taken_into_account).

## What happened

Deliverable 9 of the solution outline declared `module: pm-workflow`, but two of its five affected files
(`PendingEntrySchemaParityTest.java`, `AuditSchemaParityTest.java`) live in `pm-core`, and its own verification
ran `test -pl pm-core -am` as well. Task planning derives the module_testing build target from the module field,
so the planned build would have tested `pm-workflow` only and missed the `pm-core` edits.

## Resolution in this plan

The operator chose to split the deliverable per module: D9 (pm-workflow) and a new D10 (pm-core), renumbering
the later deliverables (12 deliverables in total).

## Candidate rule

When authoring an outline deliverable, derive its `module` from the owning module of every affected file; if the
files span more than one module, split the deliverable per module (or declare each module) so the per-module
build target covers every edited file.
