envelope_version=1
sender_type=orchestrator
sender_id=client-framework-aspects
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:04:51Z

> Routed from epic `client-framework-aspects` (repository Token-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction. Original message `plan-12-documentation-review-consolidation-001.md`, sender plan `plan-12-documentation-review-consolidation`, created 2026-11-23T20:27:56Z. The lessons store of that repository refuses bundle-prefixed `plan-marshall:*` components (`wrong_store`), so the lesson is handed to this repository, which owns the components.

# Candidate lesson: doc consolidation must protect every target linked from packaged resources

Source signal: Q-Gate finding d5d555 (3-outline, scope_criterion_validator, under_coverage, severity error), resolution taken_into_account.

## Observation

The outline's condense-not-delete rule protected only ADRs cited by production or test source. Both
`src/main/resources/META-INF/quarkus-config-doc.adoc` files (validation-quarkus, client-quarkus) link ADR files
by path. Those resources were listed as survey-only, so deleting a linked ADR would either break the zero-hit
criterion or force an edit to a packaged production resource that the request excluded.

## Resolution in this run

A path-stable group (c2) was added covering every doc/ADR linked or cited from `src/main/resources`
(ADR-0008/0015/0017/0030, token-sheriff-validation/doc/api-reference.adoc). Resources are never edited; a broken
link is fixed doc-side.

## Candidate rule

When a documentation-reduction plan deletes or moves docs, derive the protected (path-stable) set from ALL
inbound links, including packaged resources under `src/main/resources`, not only from Java source citations.

Component hint: plan-marshall:phase-3-outline (outline authoring for doc-reduction plans) or project-local docs convention.
