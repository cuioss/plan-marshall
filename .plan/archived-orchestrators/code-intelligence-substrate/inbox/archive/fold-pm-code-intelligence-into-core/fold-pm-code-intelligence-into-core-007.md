envelope_version=1
sender_type=plan
sender_id=fold-pm-code-intelligence-into-core
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-25T21:12:57Z

# An error-severity finding filed after the metrics close stays pending past merge

## Context

Q-Gate finding `8d44fd` — severity `error`, phase `6-finalize` — was filed at `2026-08-25T20:22:22Z` and is still `pending`. By that time PR #1348 had already merged (`9aaf22d8f`), `branch-cleanup` had recorded `done`, and the `6-finalize` metrics row had been closed at `19:52:24Z`, 30 minutes earlier.

Every other finding in the plan is resolved: 0 pending across the 10 plan-level findings, and 0 pending in the `2-refine`, `3-outline` and `5-execute` Q-Gate stores. This one finding is the sole pending record, and it is the most serious one filed in the run.

## Root cause

The `pending_findings_blocking_count` invariant gates phase transitions, but by the time this finding was filed there were no gated transitions left ahead of it. A finding filed after the merge has no gate in its own plan that can act on it, so `error` severity buys nothing. The dispatch brief for this retrospective also stated that all nine findings filed during the run were resolved — which is how a pending error stays invisible: the claim was asserted rather than read back from the store.

## Proposed action

Either (a) have finalize re-read the findings store after `branch-cleanup` and route any still-pending `error` finding into the epic inbox as an explicit carry-out rather than leaving it pending in an archived plan, or (b) refuse to archive a plan holding a pending `error`-severity finding, the same fail-closed shape `delete-plan`'s lesson carry-back veto already uses.

## Evidence

- `manage-findings qgate list --phase 6-finalize --resolution pending` returns exactly 1 of 10: `8d44fd`, severity `error`, `resolution_detail: null`
- `manage-findings list --resolution pending` returns 0 of 10 plan-level findings
- finding timestamp `2026-08-25T20:22:22Z` vs `6-finalize` `end_time: 2026-08-25T19:52:24Z` vs merge commit `9aaf22d8f`
- `delete-plan`'s carry-back veto is the existing precedent for refusing a terminal action that would strand a record
