envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:14Z

# Count companion-repository files in the retrospective footprint

**Signal source**: plan-retrospective (artifact-consistency, manifest-decisions, outline-vs-shipped, request-result-alignment), finalize step of workflow-dsl-parser-and-ast.

**Component (suggested)**: `plan-marshall:plan-retrospective` (shared footprint resolver `_footprint_resolver.py`)

**Category (suggested)**: improvement

## Context

Deliverable 5 changed files in the sibling repository plan-marshall-documentation (commits ed8da4c, 8f0d266, 8c5237d; PR plan-marshall-documentation#27). The outline declared them as `../plan-marshall-documentation/doc/...` paths. Every footprint-consuming aspect then graded them as unrealised: artifact-consistency recall 87.5% with 8 "missing" paths, manifest-decisions rule M6 `fail` (8 declared-but-unrealized), outline-vs-shipped 12 of 17 include_unrealised members are doc-repo paths, and request-result-alignment grades D5 `partial` at 0% coverage.

## Root cause

The footprint resolver tiers (live diff, realized capture, merge commit, PR landing) only read the plan's own repository, so a declared path that resolves outside it can never be realized. The aspects cannot tell "work not done" from "work done in another repository".

## Proposed action

Either (a) classify declared paths that resolve outside the repository root as `out_of_repo` and exclude them from recall, M6 and outline-vs-shipped denominators with an explicit published count, or (b) let a deliverable name its companion repository and branch/PR so the resolver can read that repository's diff as an extra tier. At minimum, publish the out-of-repo count so the mismatch is attributable instead of reading as a silent descope.

## Evidence

- aspect: artifact_consistency — missing[8] all `../plan-marshall-documentation/...`
- aspect: manifest_decisions — declared_vs_realized_set fail, outline_only_count 8
- aspect: outline_vs_shipped — include_unrealised 17 of 73, 12 doc-repo paths
- aspect: request_result_alignment — D5 partial at 0% despite three commits in the documentation repository
- Related but distinct from lessons-capture 009 (that one asks for cross-repository PR support in ci / phase-3-outline; this one is the retrospective's measurement)

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-015.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
