envelope_version=1
sender_type=plan
sender_id=the-comment-pipeline-on-the-way-in
epic=review-apparatus
kind=candidate-lesson
created=2026-09-24T16:20:26Z

component=plan-marshall:phase-6-finalize
category=bug
title=Keep calling record-dispatch-boundary with --step-id on every finalize dispatch

# Keep calling record-dispatch-boundary with --step-id on every finalize dispatch

## Context

In the-comment-pipeline-on-the-way-in, `work/metrics-dispatch-boundaries-6-finalize.toon` holds only 6 rows, all between 2026-09-23T19:35Z and 20:11Z. Finalize kept dispatching on 2026-09-24 (plugin-doctor twice, create-pr, automatic-review three times, triage twice), and none of those dispatches left a boundary row. All 17 boundary rows in the plan (4-plan, 5-execute, 6-finalize) carry no `--step-id` and no context-load columns.

## Root cause

The finalize dispatcher's boundary recording is not tied to every dispatch return. After the loop-backs it stopped being called, and no call site passes `--step-id`.

## Proposed action

Make the per-dispatch boundary write part of the dispatcher's return handling for every dispatched step, including loop-back re-entries. Always forward `--step-id` and the four context-load figures. Add a retrospective check that compares finalize `[DISPATCH]` lines against boundary rows.

## Evidence

- aspect: logging_gap_analysis: 6-finalize has 6 boundary rows and none after 2026-09-23T20:11Z; 17 of 17 rows keyless
- aspect: execution_context_dispatch_audit: channel confidence low (7 finalize dispatch lines vs 42 completions); firing comparison paired 0 of 17 boundary rows
