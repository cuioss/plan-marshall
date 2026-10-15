envelope_version=1
sender_type=plan
sender_id=antigravity-execution-fidelity
epic=live-blockers
kind=candidate-lesson
created=2026-10-14T21:31:49Z

component=plan-marshall:ref-workflow-architecture
category=improvement
title=Corroborate DISPATCH emissions through the resolve seam

# Corroborate DISPATCH emissions through the resolve seam

## Context

The antigravity-execution-fidelity dispatch audit paired 72 resolve records
against 72 DISPATCH lines with zero delta, yet every line was a foreign-caller
emission (foreign_caller_line_total 72, corroboration uncorroborated). A
hand-written line cancels a missing seam emission, so the clean shape verdict
is consistency of one emitter's output, never proof every dispatch was
recorded.

## Root cause

DISPATCH lines are written by callers rather than by the resolve seam itself,
so agreement between the two surfaces cannot corroborate completeness.

## Proposed action

Emit the DISPATCH work-log line from the `effort resolve-target` seam
alongside the decision-log record, so every counted line is seam-corroborated
by construction.

## Evidence

- aspect: execution-context-dispatch-audit — shape_violation 0/72 with corroboration uncorroborated and foreign_caller_line_total 72
- confidence: medium; source plan: antigravity-execution-fidelity
