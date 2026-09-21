envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T07:22:12Z

component=plan-marshall:manage-metrics
category=bug
title=record-dispatch-boundary stamps now(), so an honest backfill fabricates the timeline every correlator reads

# A backfilled dispatch-boundary row is indistinguishable from a live one, and carries the wrong time

## Context

Four of the fourteen `6-finalize` dispatch-boundary rows carry timestamps `22:10:25`, `22:10:27`, `22:10:29` and `22:10:30` — a 5-second span. They describe `pre-submission-self-review` dispatches that terminated between 19:47 and 22:09. They were backfilled by hand after the operator noticed the step had not recorded itself.

## Root cause

`record-dispatch-boundary` stamps `now()` and declares no `--terminated-at` parameter and no backfill marker. A truthful reconstruction of a lost record is therefore not expressible in the schema, and the reconstruction that IS expressible silently corrupts the one field every downstream correlator keys on. `plan-retrospective`'s dispatch audit, `check-manifest-consistency`, and `analyze-logs`' `dispatch_boundaries` block all correlate by timestamp.

## Proposed action

Add `--terminated-at ISO8601` and a `backfilled: true` column. Absent `--terminated-at`, keep stamping `now()`. A row without the marker is a live record; a row with it is a reconstruction, and every consumer can decide whether to trust its position in the timeline.

## Evidence

- aspect: execution-context-dispatch-audit / logging_gap_analysis gap LG4
- `work/metrics-dispatch-boundaries-6-finalize.toon` rows 5-8
- The same defect shape applies to `manage-findings qgate add`, which also stamps `now()` — the 21:14 finding cluster is likewise a mix of contemporaneous and reconstructed records with no way to tell them apart
