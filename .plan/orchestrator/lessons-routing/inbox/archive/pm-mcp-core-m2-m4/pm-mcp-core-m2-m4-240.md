envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T17:39:57Z

# Treat declared sibling-repo paths as cross-repo, not as unrealized footprint

**Source plan:** plan-21-entity-addressing (PR #54, merged b25d115)
**Signal source:** plan-retrospective (aspects artifact-consistency, manifest-decisions rule M6, request-result-alignment)
**Suggested component:** plan-marshall:plan-retrospective (footprint consumers; possibly plan-marshall:manage-references declared footprint)
**Category:** bug
**Confidence:** high

## Context

Deliverable 6 of plan-21 declared two files in the sibling repository `plan-marshall-documentation` (`../plan-marshall-documentation/doc/implementation-watch/workflow-dsl.adoc`, `../plan-marshall-documentation/doc/roadmap.adoc`). The work was done and opened as plan-marshall-documentation#56. The retrospective still graded both files as declared-but-unrealized: artifact-consistency recall 92% (24/26), manifest rule M6 `declared_vs_realized_set` = fail (warning), and request-result alignment graded deliverable 6 `partial` at 0% coverage.

## Root cause

The realized footprint is captured from this repository's git state only, while the declared footprint keeps paths that resolve outside the repo root. The comparison has no third bucket for "declared in another repository", so a cross-repo deliverable is graded as missed by construction.

## Proposed action

Partition declared paths that resolve outside the repo root (a leading `../<repo>/`) into a `cross_repo` set before the declared-vs-realized comparison, publish its size, and exclude it from recall, M6 and the coverage denominator. Optionally record the sibling PR (here plan-marshall-documentation#56) as the evidence for that set.

## Evidence

- aspect: artifact-consistency: `missing[2]` are exactly the two `../plan-marshall-documentation/...` paths; `references_only[0]`
- aspect: manifest-decisions: M6 fail, culprits = the same two paths
- aspect: request-result-alignment: deliverable 6 partial, all other deliverables fulfilled
- This pattern recurs for every pm-mcp-core plan whose last deliverable updates the documentation repository.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-21-entity-addressing-007.md` from plan plan-21-entity-addressing (PLAN-21, #54; Claude Code)
