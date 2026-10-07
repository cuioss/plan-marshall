envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:18:33Z

# Build-time oracle holds no row for a plan whose own log records 139 build calls

component: plan-marshall:manage-change-ledger
category: bug
confidence: high

## Context

`analyze-logs` reports this plan's `build_time` block as `total_build_seconds: 0.0`, `build_count: 0`, with every outcome bucket (`pass`, `error`, `timeout`, `killed`, `status_unknown`) at zero. Its `build_count_reconciliation` block is honest about why: `ledger_available: false`, because "the change-ledger holds no row for this plan, so the oracle build count is unmeasured rather than zero; no agreement verdict is rendered".

The same script, from the same plan directory, counts `log_build_calls: 139` — 99 `pyproject_build` and 40 `build_server` invocations. The plan's `build-results/` tree carries 45 build log files. The folded global logs attribute 29,068,380 ms to `pyproject_build` across 138 calls and 11,062,310 ms to `build_server` across 60 — together 76% of all recorded script time.

So the build-time oracle holds nothing for a plan that spent roughly eleven hours building.

## Root cause

Not established here. The change-ledger simply carries no row for this plan id, while the wrapper invocations that should have written those rows are plainly logged. Candidates: the ledger write is conditional on a code path this plan did not take; the ledger is keyed on something other than the plan id the reader queries (this plan ran in a worktree, and the retrospective read from the main checkout); or the writes went to a store the reader does not resolve.

The downstream behaviour is correct and worth preserving: `plan-efficiency` renders `total_build_seconds` as `unavailable` rather than `0`, exactly as its contract requires, so no cross-plan roll-up will average this plan in as having built instantly. The defect is upstream of that — the honest `unavailable` is covering for an oracle that should have had the answer.

## Proposed action

1. Establish why no ledger row exists. The worktree-versus-main-checkout store resolution is the first thing to test, since this plan ran with `use_worktree: true` and the retrospective read from the main checkout.
2. Make the disagreement visible where it occurs rather than only in a retrospective. `analyze-logs` already computes both figures; have `build_count_reconciliation` emit a finding when `ledger_available: false` **and** `log_build_calls > 0` — an oracle that holds nothing for a plan with 139 logged build calls is a measurable contradiction, not merely an absence.
3. Keep the `unavailable`-not-zero rendering unchanged; it is the part of this pipeline working as designed.

## Evidence

- aspect: log_analysis — `build_time.build_count: 0`, `ledger_available: false`, beside `log_build_calls: 139`
- aspect: log_analysis — `script_cost_rollup` ranks `build_server` at 19.1% and `pyproject_build` at 8.8% of plan-local script time; the folded global rollup puts `pyproject_build` at 55.2%
- artifact: 45 files under `build-results/` in the plan directory
- aspect: plan_efficiency — `total_build_seconds: unavailable` with provenance recorded
