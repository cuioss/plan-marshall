envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-21T14:02:16Z

component=plan-marshall:phase-3-outline
category=improvement
created=2026-11-21
bundle=plan-marshall
title=Check that a named owner's text carries the item before a plan records "owned by"

# Check that a named owner's text carries the item before a plan records "owned by"

## Context

The landing message of PLAN-V2-165 records two follow-ups as owned by another staged plan: "the start-failure rule stays with PLAN-V2-162 Deliverable 1" and "per-line source offsets are owned by PLAN-V2-162 item 42(c)". The orchestrator's read of that spec found that Deliverable 1 and item 56 carry only the wiring of `startFailed`, not the question of a never-connected worker, and that 42(c) names only the symptom and a narrower catch, not the offsets.

## Root cause

The plan's Done-when asks for an outcome per follow-up ("adopt, drop, or name the staged plan that owns it") but nothing reads the named plan to confirm it carries the item, so a name can stand for an owner that does not exist.

## Proposed action

When a deliverable names an existing staged plan as the owner, have the outline (or the functional review) grep that spec for the item and fail the claim if the text is absent; otherwise the follow-up stays unowned and must be adopted or dropped.

## Evidence

- aspect: landing message of plan-v2-165-supervisor-end-path-closeout, section "Residue", outcomes paragraph
- aspect: plans/PLAN-V2-162 lines 38, 110, 122 at the time of the landing
