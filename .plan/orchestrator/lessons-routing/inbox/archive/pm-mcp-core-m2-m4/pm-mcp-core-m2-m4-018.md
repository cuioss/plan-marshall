envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:05Z

# Candidate lesson: phase handshake reported drift as a script failure when the outline was re-entered with open findings

- Component: plan-marshall:plan-marshall
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-08-002 (created 2026-10-10), epic pm-mcp-core-m2-m4

Source record: work log entry `88b36d` (2026-10-09T21:48:24Z, level ERROR), the only `script_failure` marker in this plan's work log.
Plan: `workspace-confinement` (PLAN-03), pull request https://github.com/plan-marshall/pm-mcp-core/pull/19, merged.

Note on the count: the step that handed this work over did not scan the work log for failing scripts and forwarded 0 as "not measured". Reading the log for this message found exactly one failing script notation. No `[FAILED]` line and no checkpoint reclassified to an error was found.

## What the record says

`[ERROR] (plan-marshall:execute-script:1) script_failure notation=plan-marshall:plan-marshall:phase_handshake exit_code=1 failure_kind=script_internal_failure`, with the detail `status: drift`, `phase: 2-refine`, `override: false`, `drift_count: 1`, and one differing invariant: `pending_findings_blocking_count` captured `0`, observed `8`.

## Context from the log

- 21:38Z: the validator had filed 5 findings against `3-outline`; 21:47Z: the operator's review added 3 more (decision log `12b2cd`). That makes 8 pending.
- 21:47:18Z: the outline was handed off again (work log `06acc0`).
- 21:48:24Z: the handshake check failed with the drift above.
- 21:50Z: all 8 findings were resolved and the outline completed with 4 deliverables.

## Reading (not established by the log)

The 8 observed pending findings equal the 8 findings the re-entered outline was dispatched to resolve, so the drift looks like the expected state of a re-entry after review rather than a defect in the plan. The log does not say how the run got past the failed check (`override: false`), and the entry is classified `script_internal_failure`, which does not describe a drift verdict.

Classification is left to the pickup.
