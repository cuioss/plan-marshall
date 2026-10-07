# PLAN-183 Landing — Carried Defects and Watches Closure (terminal)

plan: PLAN-183 / `carried-defects-and-watches-closure` (WS-03)
pr: #1602 — `fix-close-carried-defects-and-watches-backlog-PLAN-183`
state: merged (merge_commit_sha 4ef2efd2f51bbe001dcb0594b894543ef004ebe2, squash via platform merge queue)
date: 2026-09-24

> **Terminal landing.** All eight D-rows closed; the epic's unowned-finding
> count for this backlog is zero. PLAN-183 transitions to `shipped` on this
> record. Remaining epic work lives elsewhere: RUNNING PLAN-182 (campaign
> slices 2+) and the orchestrator-owned settled.md ref repair.

## What landed

D1 gate re-derive (469/2/467 at dispatch) + kwarg-shortcut removal with
behavior-proving replacement + 2 live `subprocess-pythonpath` errors fixed;
D2 `OPERATION_REGISTRY`/`list_operations()` on `_dispatch`, router tests
registry-derived; D3 vacuous-clean (no inline parser rebuild at HEAD); D4
surfacer blind spots closed by detection (`async def`, `module_docstring`
context) with behavior probes; D5 `uv.lock` in-sync + single marshal-json
builder; D6 per-rule `###` sections for all 7 test-conventions rules; D7
DEFER flip (counts 427/21/19 non-zero, conditioned on zero — re-check at
zero); D8 `ruff format --check` gate in `build.py` quality-gate. Fix commit
5f4f73cb6 carried review triage (5/5 CodeRabbit threads replied + resolved;
Sourcery rate-limit notice only, zero findings).

## Verification (re-derived from ground truth at reconcile)

- PR #1602 `state: merged`, `merge_commit_sha` matches the plan's claim
  exactly, title/body match the PLAN-183 D-rows — read via the CI
  abstraction, never parroted.
- Landing arc drains coherently: 001 (impl-complete, PR deferred) → 003
  (CI/review dispositions) → 002 (triage + fix commit) → 004 (merge-queue
  status) → 005 (final landing with merge SHA). Landing-check semantics hold
  (complete machine-readable facts in 005).
- Inbox drained 5/5, archived under the per-sender layout. Candidate content
  rides the messages; no separate lesson allocation was owed (008-style hints
  aside, none filed here).
- Local plan archived (normal_completion), worktree removed, branch pruned
  (remote head deleted by queue) — plan-side cleanup verified as reported.

## Overrulings (operator-invited judgments, ruled here)

1. **switch-and-pull skip: UPHELD.** Main stays behind origin until the drain
   settles — pulling would require stashing foreign in-flight work (same
   dirty-tree limitation met twice before on this ledger). Reconciliation
   above proceeded from remote reads; nothing was asserted from a stale
   checkout. Health check, not a failure.
2. **Rule2 test edit as D1 scope + 002 re-allocation: SOUND.** The edited test
   IS the kwarg behavior test D1's Done clause names — in-scope by the spec's
   own words. The re-allocated 002 carries current triage content with
   PR-update history preserved; the 001→003→002→004→005 sequence
   reconstructs without gaps and archives collision-free. Future
   re-allocations should use `inbox supersede` for machine-readable
   tombstones instead of bare re-use.

## Residue (not this plan's)

- RUNNING PLAN-182 (slices 2+, B1–B4, runs 4–7 under N=1).
- 7 settled.md dangling `landings/` refs — orchestrator-owned staging-pass
  work, still open.
- Operator commit-scope decision on uncommitted paths — still open.
- The 2 declined-but-valid CodeRabbit hardenings (from the slice-1 record)
  remain epic candidates for follow-up scheduling.
