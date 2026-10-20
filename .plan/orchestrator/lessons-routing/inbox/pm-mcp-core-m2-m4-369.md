envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:03Z

component=plan-marshall:phase-3-outline
category=anti-pattern

# Outline omitted the developer guide of a package whose public signature it changes

Source: Q-Gate 3-outline finding 436a4e (resolved in run, taken_into_account), plan plan-70-plan-instance-alignment.

D8 changed the signature of `CompiledInvariants.check` (new lane input) and `ProjectUnitLoader` (package `workflow.unit`) passes the unknown lane, but `pm-workflow/doc/developer/workflow-unit.adoc` - which describes stage 6 of the project load in terms of that call - was in no deliverable. The project CLAUDE.md requires a plan to write the developer documentation of every package it changes.

## Rule

For every package whose code a deliverable changes, the outline's footprint must list that package's `{module}/doc/developer/{package}.adoc` (or state why it stays unchanged). Derive the set from the changed callers too, not only from the class whose signature moves.
