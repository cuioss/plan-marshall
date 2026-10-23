envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:34Z

component=plan-marshall:manage-solution-outline
category=improvement
confidence=high
source=plan-retrospective (artifact-consistency, manifest-decisions, request-result-alignment, llm-to-script-opportunities)

# Amend declared affected files when a Q-Gate or operator decision widens scope

## Context

Six realized files were never in the outline's declared surface: `13-leases-integrity-testing.adoc` (added by TASK-1 to resolve 4-plan Q-Gate finding f08c33), `IntegrityKeyCarry.java` and ADR runtime-credentials/006 (the operator's finalize decision to fix the first-recording key gap), plus `doc/adr/README.adoc`, `CredentialAccount.java` (declared read-only) and `CredentialStoreChoiceFixture.java`. The scope-creep guard re-reported the same set in every later envelope and triage, and every functional-review round re-graded the same six "unrequested changes".

## Root cause

A sanctioned widening (an accepted Q-Gate finding or an operator decision) has no path back into the outline's declared file list; `sync-affected-files` only adds paths the outline already names, so the declared set stays frozen at the pre-widening state.

## Proposed action

Add an amend path (for example a `manage-solution-outline` verb) that records a sanctioned widening against its deliverable with its provenance (Q-Gate hash or decision-log id), so scope-creep, artifact-consistency and the functional review see it as declared once instead of re-litigating it each round.

## Evidence

- aspect: artifact-consistency — references_only 6 paths, outline_only 0
- aspect: manifest-decisions — declared_vs_realized_set fail (6 realized-but-undeclared)
- aspect: request-result-alignment — scope creep 6 files over the 5-file tolerance
