envelope_version=1
sender_type=plan
sender_id=retrospective-aspects-publish-verdict
epic=post-run-quality
kind=candidate-lesson
created=2026-09-21T09:26:34Z

component=plan-marshall:manage-change-ledger
category=bug
confidence=high
title=Build rows never reach the change-ledger, so build_time is unavailable on every plan

# Build rows never reach the change-ledger, so build_time is unavailable on every plan

# CORROBORATION, NOT A NEW FIX - coordinate with PLAN-PRQ-08 D0

## Context

PLAN-PRQ-02 D2 moved the "absent is not zero" duty to the producer: `analyze-logs`
now emits the literal `unavailable` for `total_build_seconds` instead of a false `0.0`.
That fix WORKS and this run demonstrates it.

It also demonstrates that the fix was necessary but not sufficient, exactly as folded
lesson `2026-09-04-08-008` predicted. On this run:

- `ledger_present: true`, `ledger_readable: true`, `ledger_rows_scanned: 796`
- `summed_rows: 0`, `build_count: 0`, `total_build_seconds: unavailable`
- but the plan's own script log recorded **27 build calls**
  (15 `build-pyproject:pyproject_build`, 12 `build-server-client:build_server`),
  and the folded global logs rank `pyproject_build` as the single largest cost at
  18,859,110 ms across 167 calls

So the ledger was present, readable, and scanned 796 rows, and held no build row for
this plan while builds demonstrably ran. The honest sentinel now names the gap instead
of hiding it behind a zero — which is precisely what makes the writer-side gap
measurable for the first time.

## Root cause

The change-ledger build-row WRITER does not record build executions. Nothing on the
read side can repair this; publishing the population truthfully still reports nothing
while nothing writes rows.

## Proposed action

None from this plan — the ledger half is PLAN-PRQ-08 D0's declared subject and the spec
says explicitly "coordinate, do not duplicate".

What this message adds is FIRST-PARTY POST-LANDING EVIDENCE for PRQ-08's premise, with
the exact figures above, and a ready-made acceptance test: after PRQ-08 D0 lands, a
plan that runs N builds must report `summed_rows == N` and a numeric
`total_build_seconds`, on this plan's own recorded 27-call baseline.

## Evidence

- aspect: log_analysis — `build_time` block: ledger present/readable, 796 rows scanned, 0 build rows
- aspect: log_analysis — `log_build_calls: 27` with per-notation breakdown
- aspect: plan_efficiency — `total_build_seconds: unavailable` surfaced verbatim with its population
- prior art: folded lesson `2026-09-04-08-008`, spec D2's FOLDED note
