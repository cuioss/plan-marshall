envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-15T18:07:58Z

# A commit the phase-5 orchestrator makes for a quality-gate rewrite or a style fix has no change-ledger row, so the 5-execute -> 6-finalize transition refuses

**Severity:** high (orchestrator grade, 2026-11-15 drain of the lessons-routing inbox)
**Bundle:** plan-marshall (`workflow-integration-git` `git-workflow commit`, `manage-status` transition guard, `phase-5-execute` orchestrator-tier hand-back)
**Checked at:** `34b92e0ca` (origin/main)

## What was reported

Three pm-mcp-core plans in three days ended phase 5 with a commit the orchestrator made OUTSIDE the per-deliverable settlement, and each one was refused at the transition with `error=execute_commits_unrecorded signature=bookkeeping_gap`:

- `plan-v2-57-default-plan-lanes-and-run` (2026-11-11): `verify -Ppre-commit` rewrote two test files, committed as `c6c1767f`. 1 of 6 branch commits had no `kind=change` row. The re-dispatched execute leaf returned `status error` and asked the operator how to attribute a commit that spans two deliverables. The dispatch ended with `termination_cause=error` and 136,153 tokens.
- `plan-v2-132-coverage-parser-hardening` (2026-11-12): the orchestrator ran the whole-tree `verify -Ppre-commit` after the hand-back and committed its rewrites (`f5f1931c`, 5 files) plus a Javadoc fix (`1f80e2ab`). 2 of 7 branch commits had no row. `termination_cause=error`, 146,533 tokens, rows appended by hand.
- `plan-v2-40-envelope-packing` (2026-11-12): an import-order style commit (`4d9ff969`) and the whitespace rewrite of the pre-commit gate (`f87166ef`). 2 of 7 unrecorded. The refusal payload named each SHA with its own append call, so the repair was two `manage-change-ledger append --kind change` calls, and the whitespace commit also made the freshness gate stale, forcing a whole-tree re-verify.

## Ground truth at the checked commit

`marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py:1033-1046`: `_record_finalize_change` appends the row "ONLY in `6-finalize`", and its docstring states why: at the `5-execute` boundary "`current_phase` is still `5-execute`, so the settlement owns its own row". A commit the orchestrator makes during phase 5 outside Step 10a, through this verb or raw, is therefore owned by nobody.

`PLAN-LB-126` (shipped, #1942) closed the FINALIZE half: dispatcher item 5f(b), the triage inline fix and the architecture refresh now write their own rows. Its Deliverable 1 keeps the phase gate (appends only when the plan's `current_phase` is `6-finalize`), so it does not reach a phase-5 hand-back commit. The refusal itself still exists and still counts every branch commit.

No other `live-blockers` plan or message owns this: `PLAN-LB-91` (shipped) is the history-rewrite remap, and `PLAN-LB-146` is about which tree a build result names.

## What is asked

Give the commits the orchestrator makes at the orchestrator-tier hand-back (gate rewrites, style fixes, Javadoc fixes made after the envelope) one owner that writes their `kind=change` row at the point they are made, with a `deliverable_id` no reader mistakes for an outline deliverable. Either the commit verb appends in `5-execute` when the commit is made outside Step 10a, or the hand-back workflow commits gate output through a path that ledgers it. A commit that spans two deliverables must not need an operator decision.

## Sources

- `pm-mcp-core-m2-m4-v2-009`, `-021` and `-023`, archived verbatim at `lessons-routing/inbox/archive/pm-mcp-core-m2-m4-v2/`.
- Related and already owned: `api-sheriff-api-sheriff-0-2-0-081` item 2 (a finalize-simplify commit with no row) is the finalize half, fixed by `PLAN-LB-126`.
