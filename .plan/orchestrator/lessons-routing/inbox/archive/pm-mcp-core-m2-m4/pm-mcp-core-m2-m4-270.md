envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-14T13:31:57Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan static-verifier-residuals (PLAN-56, pm-mcp-core #66, merged 7981d17), drained 2026-10-14.
> Source inbox message(s): static-verifier-residuals-009.md 
> RECURRENCE of lessons-routing inbox messages already routed by this epic: pm-mcp-core-m2-m4-220 (queued); -079 (archived). Fold into those; this is new evidence from another plan, not a new lesson.

component=plan-marshall:phase-3-outline
category=bug
title=Record read-intent references as context assessments, not CERTAIN_INCLUDE

# Record read-intent references as context assessments, not CERTAIN_INCLUDE

## Context

After the outline Q-Gate flagged "no assessments", the outline fix pass recorded 48 CERTAIN_INCLUDE assessments, "one for each affected file", including the files the deliverables declared `(read)`. The outline-vs-shipped aspect then reports 9 of 47 CERTAIN_INCLUDE paths as include_unrealised (ADR 007, GuardSpec, WorkflowParser, WorkflowPrinter, RemediationInvariants, SchemaRegistry and three existing refused fixtures). Every one of the 9 is a read-only reference that was never meant to change.

## Root cause

Assessment recording does not distinguish write intent from read intent, so a read-only reference is graded as an expected modification and inflates the include_unrealised (silent-descope) signal.

## Proposed action

When phase-3-outline records assessments from declared files, record `(read)` bullets with a non-include certainty (or skip them), and let check-outline-vs-shipped exclude read-intent paths from the include_unrealised population.

## Evidence

- aspect: outline-vs-shipped — include_unrealised 9 of 47, all 9 declared `(read)` in solution_outline.md
- aspect: artifact-consistency — recall 100% over 35 modification-intent files with read_intent_excluded 12, so no declared write was missed
- outline fix-pass report: "48 CERTAIN_INCLUDE assessments are now recorded, one for each affected file of this repository in deliverables 1-8"
