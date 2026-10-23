envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T10:23:49Z

component=plan-marshall:phase-5-execute
category=bug
created=2026-10-18

# Check upstream drift against pending tasks' declared files, not only commits

## Context

Execute envelopes 1 to 4 of plan-20-job-runner each ran the baseline probe, found origin/main ahead (5197490 #84, c281f6c #85, e47becc #87, 065001e #88) and absorbed the new main_sha into metadata only because `baseline-reconcile` reported `conflict_count: 0`. Envelope 1 already noted that #84 changed four specification files TASK-19 would edit later. Envelope 5 then stopped TASK-19 as blocked (worktree lacks upstream commits) and spent 202,139 tokens; the orchestrator had to merge main before re-dispatching it.

## Root cause

The overlap check compares upstream changes only against files the branch has already committed. It does not compare them against the declared affected files of tasks still pending, so a known future conflict reads as "no conflict" until the task that owns the files runs.

## Proposed action

Extend `baseline-reconcile` (or the envelope-entry probe) to union the declared affected files of pending tasks into the overlap set, and report `conflict_count > 0` when upstream changed one of them, so the drift is resolved at the first envelope that sees it. Record a dispatch stopped for this reason with termination cause `baseline_drift`, not `error`.

## Evidence

- aspect: logging_gap_analysis - 5-execute boundary row 22:08:23Z recorded `error`, 202139 tokens, for the TASK-19 upstream block
- aspect: chat_history_analysis - envelope 5 report "TASK-19 blocked: worktree lacks upstream commits 5197490..065001e", conflict_count 0
- aspect: llm_to_script_opportunities - baseline probe re-ran in 4 envelopes without seeing the overlap
