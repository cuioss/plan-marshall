envelope_version=1
sender_type=plan
sender_id=lb-37-functional-review
epic=live-blockers
kind=candidate-lesson
created=2026-10-13T13:52:21Z

component=plan-marshall:phase-6-finalize
category=bug
title=Record execution-log and dispatch-boundary rows on every finalize re-fire

# Record execution-log and dispatch-boundary rows on every finalize re-fire

## Context

In lb-37-functional-review the review steps fired 11-12 times each (functional-review 12, code-review 11, lessons-housekeeping 11, plugin-doctor 11), yet `execution_log` holds only 17 6-finalize rows, the last at 2026-10-12T09:15, and `metrics-dispatch-boundaries-6-finalize.toon` holds 3 rows. The dispatch audit rates channel confidence low (9 finalize dispatch lines against 74 completions).

## Root cause

The Step 3 item 5b/5c/5e calls (accumulate-agent-usage, record-dispatch-boundary, record-step) are prose obligations the orchestrator skipped on re-fires driven from loop-backs and from the out-of-plan stack landing; nothing checks that a terminal mark-step-done was paired with a record-step row.

## Proposed action

Fuse the record-step row to the terminal mark-step-done write for 6-finalize (as the completion line already is), or have the completion guard (item 5d) refuse to advance when the step's latest firing has no execution_log row.

## Evidence

- aspect: logging_gap_analysis - 3 boundary rows vs 74 finalize completions; execution_log stops after 2026-10-12T09:15
- aspect: execution_context_dispatch_audit - channel_completeness ratio 0.122, confidence low; 8 of 14 steps no_evidence
- aspect: plan_efficiency - per-step cost of the review loops is unmeasured
