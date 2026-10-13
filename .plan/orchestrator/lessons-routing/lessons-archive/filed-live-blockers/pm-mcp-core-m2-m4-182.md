envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:17Z

# Candidate lesson: resolve workflow notations from the installed bundle in non-marketplace repos

Source: plan-retrospective of plan verify-not-resolve. Proposed component: `plan-marshall:execution-context`. Category: bug. Confidence: high.

## Context

The execution-context dispatcher resolves a `workflow` notation to `marketplace/bundles/{bundle}/skills/...`. `pm-mcp-core` is not the marketplace repository and has no such tree. At least three dispatched leaves reported that the workflow doc was missing at that path and read it from `/Users/oliver/git/plan-marshall/...` instead: the 4-plan leaf, and the sonar-roundtrip leaf twice.

## Root cause

The notation table in the execution-context Step 4 assumes the marketplace source layout. Consumer projects only have the installed bundle copy.

## Proposed action

Resolve the notation against the installed plugin root (the directory the loaded skill came from), with the marketplace source tree only as a development-time fallback. Return `workflow_not_found` instead of letting the leaf guess a path.

## Evidence

- aspect: chat-history-analysis — 4-plan leaf: "The workflow doc did not exist at marketplace/bundles/... in this repo"; sonar-roundtrip leaves (both runs): read from `/Users/oliver/git/plan-marshall/target/claude/plan-marshall/skills/phase-6-finalize/workflow/sonar-roundtrip.md`

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-017.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
