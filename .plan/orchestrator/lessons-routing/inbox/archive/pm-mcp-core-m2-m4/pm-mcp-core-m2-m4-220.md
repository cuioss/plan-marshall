envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T11:06:06Z

# Exclude sibling-repo and read-intent paths from footprint set checks

Component: plan-marshall:plan-retrospective (category: bug, confidence: high)

## Context

Deliverable 7 of scenario-replay-harness changed three files in `../plan-marshall-documentation` (commit 68ca167,
PR #53). The retrospective's footprint is resolved from the pm-mcp-core repository only, so
`check-artifact-consistency` reported those three as `outline_only`, `check-manifest-consistency` rule M6
(`declared_vs_realized_set`) returned `fail` with a warning, and `check-outline-vs-shipped` reported 9
`include_unrealised` paths. Eight of the nine are sibling-repo paths (three shipped, five survey-only watch files);
the ninth, `doc/plans/scenario-replay-harness.adoc`, is annotated `(read)` in the outline.

## Root cause

The footprint consumers compare declared paths against a single-repo footprint with no notion of a path outside
the repository root, and `check-outline-vs-shipped` does not apply the read-intent exclusion that
`check-artifact-consistency` already applies (`read_intent_excluded: 6`).

## Proposed action

Classify declared paths that resolve outside the repository root as a separate `out_of_repo` population (reported,
never counted as unrealised) and exclude read-intent declarations from `include_unrealised`, the same way
artifact-consistency does.

## Evidence

- aspect: artifact_consistency — outline_only[3] all under ../plan-marshall-documentation
- aspect: manifest_decisions — declared_vs_realized_set fail, culprits are the same 3 paths
- aspect: outline_vs_shipped — include_unrealised 9 of 26; 8 sibling-repo, 1 read-intent

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `scenario-replay-harness-011.md` from plan scenario-replay-harness (PLAN-22, #50; Claude Code)
