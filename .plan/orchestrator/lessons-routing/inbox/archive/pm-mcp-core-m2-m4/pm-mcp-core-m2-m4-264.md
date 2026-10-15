envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-14T13:31:53Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan static-verifier-residuals (PLAN-56, pm-mcp-core #66, merged 7981d17), drained 2026-10-14.
> Source inbox message(s): static-verifier-residuals-002.md 

# Candidate lesson: a constructor/signature change must sweep every construction site

Plan: static-verifier-residuals (PR plan-marshall/pm-mcp-core#66).
Signal source: Q-Gate findings 0b50a8 (under_coverage, error) and b85630 (over_coverage),
phase 3-outline, scope_criterion_validator.

## What happened

Deliverable 6 replaced the two-list VerificationResult constructor with a single-list one. The
outline listed RegistriesAndRecordsTest.java (which references none of the removed types) and
missed pm-workflow/.../engine/WorkflowEngine.java, which constructs
`new VerificationResult(List.of(), List.of())` at two sites (verifyWithCallees ~535 and ~817).
The build would have broken once the advisories list was removed. The 3-outline Q-Gate caught
both directions with a content sweep (`architecture search --content 'new VerificationResult('`).

## Candidate rule

When a deliverable removes or changes a constructor, record component, or public signature,
derive its affected files from a content sweep for the construction/call pattern
(`architecture search --content`), not from the outline author's recollection of where the
type is used; list every hit and drop files with no hit.

## Suggested owner

plan-marshall phase-3-outline (deep lane affected-file derivation). Classification deferred
to the orchestrator.
