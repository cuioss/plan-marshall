envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-21T14:02:15Z

component=plan-marshall:phase-5-execute
category=improvement
created=2026-11-21
bundle=plan-marshall
title=A functional-review criterion that needs the landing message cannot be met before the merge

# A functional-review criterion that needs the landing message cannot be met before the merge

## Context

PLAN-V2-165 (a plan run under an orchestrator epic) had a deliverable criterion D5.C3 that asks for the plan's landing message as its evidence. The functional review runs before the merge, the landing message (`emit-landing`) is written after it.

## Root cause

The criterion is unsatisfiable by construction at the time the review runs, so the operator had to close the review on that one criterion twice (at refine and at the first review, then again at head 42f8195f).

## Proposed action

Have the outline refuse, or rewrite, a deliverable criterion whose evidence is created after the merge (the landing message, the PR number, the merge commit), or let the functional review mark such a criterion `deferred-to-landing` and not count it as open.

## Evidence

- aspect: landing message of plan-v2-165-supervisor-end-path-closeout, section "Operator decisions and deviations", first bullet
- aspect: 30.7M tokens and four finalize re-runs after head moves
