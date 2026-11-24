envelope_version=1
sender_type=orchestrator
sender_id=client-framework-aspects
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:04:51Z

> Routed from epic `client-framework-aspects` (repository Token-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction. Original message `plan-12-documentation-review-consolidation-002.md`, sender plan `plan-12-documentation-review-consolidation`, created 2026-11-23T20:28:05Z. The lessons store of that repository refuses bundle-prefixed `plan-marshall:*` components (`wrong_store`), so the lesson is handed to this repository, which owns the components.

# Candidate lesson: a "keep unchanged" ADR must not cite an ADR the plan deletes

Source signal: Q-Gate finding 20deeb (3-outline, false_positive_check, severity warning), resolution taken_into_account.

## Observation

D3 left "keep" ADRs untouched and dropped them from the mutation set, while D11 fixed references only inside
D3-D9 mutation sets. ADRs cross-cite heavily (30 of 31 ADR files cite another ADR; ADR-0006 cited the
to-be-deleted ADR-0005), so a kept ADR citing a deleted one would keep a dangling reference and fail D11's
zero-hit criterion.

## Resolution in this run

A kept-ADR citation rule was added to D2: a keep ADR may not cite a delete ADR; each such pair is resolved by
condensing either the citing ADR (citation retargeted) or the cited one. ADR-0005 stayed delete, so every ADR
citing it was condensed.

## Candidate rule

Before classifying ADRs as keep/condense/delete, compute the ADR citation graph and enforce closure: no
untouched record may reference a record the same plan deletes. Classification and reference repair must be
planned together.

Component hint: plan-marshall:manage-adr or plan-marshall:phase-3-outline (ADR-reduction outlines).
