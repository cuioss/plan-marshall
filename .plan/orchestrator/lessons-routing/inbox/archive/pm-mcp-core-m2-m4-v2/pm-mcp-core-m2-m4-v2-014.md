envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-11T23:11:04Z

component=plan-marshall:phase-6-finalize
category=improvement
title=Scope the pre-push gate re-fire to the delta after a comment-only loop-back
confidence=medium

# Scope the pre-push gate re-fire to the delta after a comment-only loop-back

## Context

In plan-v2-57-default-plan-lanes-and-run, the wait-region triage looped finalize back once for two small commits: a header-comment rewording in `per-lane-rework.pmwf` (4a0862a0) and a null-check lambda swapped for `Objects::nonNull` in `DefaultPlanRunTest` (614e8e51). The replay re-ran functional review, code review, a whole-tree pre-push quality gate (17:37 to 18:35, about 57 min) and ci-verify (about 29 min). 6-finalize carried 2.57M of the plan's 4.39M dispatched tokens (58%). The gate went whole-tree because the spec `.adoc` path resolved to no registered module, even though that file was not part of the delta.

## Root cause

The re-fire decision is keyed on HEAD movement alone. It does not scope the gate to the paths changed since the last green firing, and an unmapped path anywhere in the plan's footprint forces the whole tree.

## Proposed action

When a re-fire's delta since the last green head touches only test or resource files of known modules, run the gate scoped to those modules. Compute the "unmapped path forces whole-tree" fallback over the delta, not over the whole footprint.

## Evidence

- plan_efficiency: max_phase_token_share 0.58, multi_module+feature error anchor tripped at 4.39M
- log_analysis: maven owns 55.7% of script time; pre-push-quality-gate firing_count 2
- work.log 16:21:03 and 18:21:12: "Footprint paths resolved to no registered module: doc/specification/... proceeding whole-tree"
