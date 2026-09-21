envelope_version=1
sender_type=plan
sender_id=ledger-joins
epic=quality-aspect
kind=candidate-lesson
created=2026-09-20T07:24:32Z

# Stamp one dispatch-boundary row per finalize-step termination

## Context

The ledger-joins retrospective found the finalize phase holds 45 execution rows but no dispatch-boundary file, so boundary/execution pairing and union_rows coverage cannot be evaluated for finalize-step dispatches.

## Root cause

Finalize-step dispatches terminate without recording a dispatch-boundary row, leaving the boundary ledger without the finalize side of the join.

## Proposed action

Stamp one dispatch-boundary row per finalize-step dispatch termination, or declare the finalize exclusion explicitly in dispatch_boundary_excluded_classes.

## Evidence

- aspect: execution-context-dispatch-audit — 6-finalize not_evaluated, no boundary file
- plan: ledger-joins — 45 execution rows vs 0 boundary rows in 6-finalize

component: plan-marshall:manage-metrics
category: improvement
title: Stamp one dispatch-boundary row per finalize-step termination
confidence: high
source_aspects: logging_gap_analysis
