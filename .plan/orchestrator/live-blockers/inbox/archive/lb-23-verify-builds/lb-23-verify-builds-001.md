envelope_version=1
sender_type=plan
sender_id=lb-23-verify-builds
epic=live-blockers
kind=finding
created=2026-10-08T22:35:01Z

# Routed builds logged for a plan leave no change-ledger row for that plan

## Observation

During the lb-14 run, 84 routed builds were written to the plan's work log, and the change ledger held zero `kind=build` rows for the plan.

## Why this is a separate defect

It is not explained by a missing plan id. The work-log line for a routed build is only written when the id names a real plan, so those 84 builds carried one. lb-23 (deliverable 5) fixes a different cause: a build resolved through `architecture resolve` and run verbatim carried no plan id at all and recorded `NO_PLAN`.

## Candidate cause

Where the row lands. `_ledger_core.resolve_ledger_path` is per working tree, so a row appended by a build that ran in one working tree is not in the ledger a reader in another working tree opens. A routed build runs under the daemon; the working tree it resolves the ledger from may not be the one the freshness gate later reads.

## Evidence pointers

- `_build_execute_factory._append_gate_build_row` (called with `route='routed'`) and `_record_resolution`
- `execute-script.py.template` `_ledger_plan_id`
- `_ledger_core.resolve_ledger_path`

## Status

Not established: the candidate cause is reasoned from the code, not reproduced. lb-23 makes no source change for it.

## Suggested next step

Reproduce with one routed build for a plan in a worktree, then read which ledger file received the row and which file `pre-commit-verify-freshness` opens for the same plan.
