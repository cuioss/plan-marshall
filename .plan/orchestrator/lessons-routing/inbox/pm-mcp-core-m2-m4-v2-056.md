envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-21T16:27:03Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-11-21
bundle=plan-marshall
title=Measure the review-thread and finding counts and the effort at the merge gate instead of writing them unknown

# Measure the review-thread and finding counts and the effort at the merge gate instead of writing them unknown

## Context

The landing facts of PLAN-V2-25 (#542) record `unresolved_review_threads`, `review_body_findings_total` and `review_body_findings_handled` as `unknown`, and `effort=unknown`, although the run did handle every thread and finding. PLAN-V2-165 and 160 show the counts when a lifecycle step measured them, so the gap depends on the path the run took.

## Root cause

No lifecycle step records these four measurements at the merge gate on every path; the landing message can only copy what an earlier step wrote.

## Proposed action

Have the pre-merge barrier (or `automatic-review` on exit) write the unresolved-thread count and the review-body finding totals into the plan status, and have the runtime stamp carry the effort value, so the landing facts never read `unknown` for a measurable figure.

## Evidence

- aspect: landing message plan-v2-25-command-record-and-dispatch-004, `landing-facts` block and Residue bullets 1 and 2
- aspect: landing messages of plan-v2-165 (`unresolved_review_threads=0`, `review_body_findings_total=2`) for comparison
