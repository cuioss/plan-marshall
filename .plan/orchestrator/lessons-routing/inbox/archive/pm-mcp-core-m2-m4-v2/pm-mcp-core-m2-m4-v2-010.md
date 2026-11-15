envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-11T23:11:03Z

component=plan-marshall:phase-6-finalize
category=bug
title=Carry prior findings forward before a delta-round code-review author writes
confidence=high

# Carry prior findings forward before a delta-round code-review author writes

## Context

During the finalize replay of plan-v2-57-default-plan-lanes-and-run, the delta-round code-review author (7 files in scope) wrote `work/code-review-findings.json` without reading the previous round's content. The author reported that the Write tool accepted the overwrite and that any earlier finding located outside the 7 delta files was lost and could not be recovered. The closing full round re-derived 5 advisory findings, so nothing blocking was lost this time.

## Root cause

The code-review workflow requires the delta author to carry forward out-of-delta findings verbatim, but nothing enforces it: the findings file is written with a plain Write, and no script merges or guards the prior round.

## Proposed action

Make the delta-round write go through a script verb that merges the new findings with the prior round's out-of-delta findings (or refuses a write that drops them), instead of relying on the author to Read first. Alternatively, have the dispatcher snapshot the prior findings file before a delta round and validate carry-forward in Step 4.

## Evidence

- chat_history_analysis: code-review author hand-back, delta round over 7 files, "I overwrote the findings file without reading its previous-round content first"
- status.json: code-review firing_count 2, final round full with 5 advisory
