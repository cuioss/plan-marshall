envelope_version=1
sender_type=plan
sender_id=truth-147-lane-reports-green
epic=truthful-signals
kind=candidate-lesson
created=2026-09-24T08:06:13Z

envelope_version=1
sender_type=plan
sender_id=truth-147-lane-reports-green
epic=truthful-signals
kind=candidate-lesson
created=2026-09-24T08:10:00Z

component=plan-marshall:phase-5-execute
category=improvement
title=Surface agent-initiated re-dispatch share in 5-execute dispatch ledger
confidence=medium
source_plan=truth-147-lane-reports-green
source_aspects=logging-gap-analysis

# Surface agent-initiated re-dispatch share in 5-execute dispatch ledger

## Context

On plan truth-147-lane-reports-green, 4 of the 5 recorded 5-execute dispatches
terminated as voluntary_checkpoint (80%) before a final clean_exit_queue_empty.
Each re-dispatch re-reads plan context, so the dominant termination mode is
also the dominant context-spend mode, yet nothing in the execute ledger names
that share at dispatch time.

## Root cause

Agents return control with pending work in the queue (voluntary checkpoint)
instead of driving to clean exit; the ledger records each cause faithfully but
no threshold names the majority share where re-dispatch stops being an
exception and becomes the execution pattern.

## Proposed action

Keep the logging-gap >50% flag, and consider an execute-side
voluntary-checkpoint budget or a per-envelope progress requirement so a
checkpoint-majority run prompts the dispatcher before the next re-dispatch.

## Evidence

- aspect: logging-gap-analysis — 5-execute dispatch distribution 4 voluntary_checkpoint of 5 rows (80% > 50% rule)
- aspect: log-analysis — dispatch_boundaries 5-execute rows with per-cause counts, unknown_count 0
