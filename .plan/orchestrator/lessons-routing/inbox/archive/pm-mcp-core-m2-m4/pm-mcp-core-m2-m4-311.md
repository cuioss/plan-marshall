envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:16:42Z

# Candidate lesson: Index project test-resource extensions such as .pmwf in the architecture inventory

Source: plan-retrospective (chat-history-analysis + llm-to-script-opportunities), plan-69-unit-frontmatter-and-types
Component (suggested): plan-marshall:manage-architecture (foreign bundle - route to plan-marshall lessons inbox)
Category (suggested): improvement

## Context

The plan migrated 124 existing `.pmwf` workflow-unit fixtures and added 46. Dispatched leaves are not granted Grep/Glob and must use `architecture find` / `architecture search --content`, but the inventory does not index `.pmwf` files (`find "*.pmwf"` returns 0). Four separate dispatches hit the same wall: refine could not recount the fixtures, the 4-plan Q-Gate recorded a `not_run_validators` entry for the `.pmwf` population criterion and wrote its hashes `--partial`, and the functional review fell back to git name-status to count them.

## Root cause

The inventory's file walk recognises only the extensions the domain extensions know, so a project's own source-like resources fall outside every leaf-reachable discovery verb, and coverage checks over them degrade to "could not look".

## Proposed action

Let a project declare extra indexed extensions (or index every tracked file under a module's `src/` at least for `find`), so `architecture find --pattern "*.pmwf"` and `search --content` reach them; until then, offer a git-tracked-file population verb leaves may use.

## Evidence

- refine dispatch: "The inventory does not index .pmwf resources, so I could not independently recount the 124 fixtures"
- 4-plan q-gate: `not_run_validators[1]: scope-criterion-pmwf-population`, hashes written `--partial`
- functional review: "The test-resource .pmwf files are outside the inventory ... I used the git diff instead"
