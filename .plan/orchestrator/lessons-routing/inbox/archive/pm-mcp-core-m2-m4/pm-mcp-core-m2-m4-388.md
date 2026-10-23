envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:09Z

component=plan-marshall:execution-context
category=bug

# Resolve workflow notations to the installed plugin path, not marketplace/bundles

Source: plan-retrospective of plan-70-plan-instance-alignment (aspect chat-history-analysis, repeated across four leaves).

## Context

The execution-context dispatcher resolves `{bundle}:{skill}/...` workflow notations to `marketplace/bundles/{bundle}/skills/...`. This consumer repository has no `marketplace/` tree, so the 4-plan leaf, the verification-feedback triage leaf, the lessons-capture leaf and others each reported the resolved path missing and read the document from the plugin cache (`~/.claude/plugins/cache/plan-marshall/plan-marshall/<version>/skills/...`) instead. Strictly applied, Step 4 of the dispatcher would have returned `workflow_not_found`.

## Root cause

The notation table in the dispatcher assumes the marketplace source checkout; it has no resolution rule for an installed-plugin consumer project.

## Proposed action

Resolve workflow notations through the same seam the executor uses for scripts (installed plugin root first, marketplace source tree only when present), and state that rule in the dispatcher's notation table so leaves stop improvising the fallback.

## Evidence

- chat-history-analysis: 4-plan leaf a5de42 "The persisted workflow path marketplace/bundles/... does not exist in this repo"
- chat-history-analysis: triage leaf a1041b and lessons-capture leaf a6c9b8 report the same and read from the plugin cache
