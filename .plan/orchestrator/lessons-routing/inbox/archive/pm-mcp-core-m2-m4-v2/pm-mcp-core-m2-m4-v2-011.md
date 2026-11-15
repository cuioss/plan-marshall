envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-11T23:11:03Z

component=plan-marshall:manage-architecture
category=improvement
title=Walk .pmwf test resources in the content inventory
confidence=high

# Walk .pmwf test resources in the content inventory

## Context

In plan-v2-57-default-plan-lanes-and-run the change set was mostly `.pmwf` workflow fixtures under `pm-workflow/src/test/resources/`. Three separate subagents (phase-3-outline, the phase-4 q-gate validation, and the finalize code review) each reported the same gap: `architecture search --content` does not cover `.pmwf` files, and `Grep` was denied to the subagent. The consumer sweeps for `test.lane`, `test.route` and `plan.land-exit` therefore could not run, and the agents fell back to reading the twelve fixture units by hand. One undeclared consumer, `pm-workflow/src/test/resources/plan/per-lane-rework.pmwf`, was only found when 8 `PlanInstanceComposerTest` cases failed in execute.

## Root cause

The content inventory's file set leaves out the `.pmwf` extension (or test-resource trees in general), so the structured-first search path has no fallback when `Grep` is not granted.

## Proposed action

Add `.pmwf` (and other text resources a project registers) to the files `architecture search --content` walks, or make the inventory's extension set configurable per project. Then the outline's consumer sweep would have caught `per-lane-rework.pmwf` up front.

## Evidence

- chat_history_analysis: outline "Search gap: the file-content search does not cover the .pmwf fixture files"; q-gate "the .pmwf fixture files ... are outside the content inventory"; code-review "the .pmwf resources are not walked by the architecture inventory, and Grep/Glob were not available to me"
- request_result_alignment: per-lane-rework.pmwf changed outside every declared surface
