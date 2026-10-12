envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:37Z

# Measure cross-repository deliverables in the retrospective footprint instead of reporting them unrealised

Component: plan-marshall:plan-retrospective (shared footprint resolver; artifact-consistency, outline-vs-shipped)
Category (proposed): improvement
Confidence: high
Source: plan code-analysis-base, post-run-review retrospective (aspects artifact-consistency, outline-vs-shipped, request-result-alignment)

## Context

D8 to D10 of this plan changed 9 files in the sibling repository plan-marshall-documentation. They were committed in a separate documentation worktree (fdc7a7c, 272fa65, 241a19b) and shipped through plan-marshall-documentation#31. The retrospective still reports them as not delivered: artifact recall is 84% with all 9 documentation paths under `missing`/`outline_only`, and outline-vs-shipped counts 7 of them as `include_unrealised`. The work was actually done.

## Root cause

The shared footprint resolver derives the realised footprint from this repository's git state only. A declared path under another repository's root can never match it, so a cross-repo deliverable is graded as unrealised by construction.

## Proposed action

Have the resolver treat declared absolute paths outside the repository as a separate population. Either resolve them against the sibling repository's commits recorded by the plan (the decision log already records the doc SHAs; a structured record would be better), or exclude them from recall and from `include_unrealised` and publish them as `cross_repo_unmeasured` with a count. This also applies to every plan in the epic that updates a specification beside its code.

## Evidence

- aspect: artifact-consistency: recall 83.9%, 9 missing paths, all under /Users/oliver/git/plan-marshall-documentation
- aspect: outline-vs-shipped: include_unrealised 13 of 21, 7 of them documentation-repo paths
- aspect: request-result-alignment: D8-D10 fulfilled per documentation commits fdc7a7c, 272fa65, 241a19b

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `code-analysis-base-015.md` from plan code-analysis-base (PLAN-36, #31)
