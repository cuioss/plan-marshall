# Landing Analysis: PLAN-CIS-038 — Frozen manifest diverges from live config

epic: code-intelligence-substrate
workstream: WS-04
pr: 1236
merge_commit: `d2e94b45a`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/190-frozen-manifest-diverges-from-live-config/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 6 of 6 deliverables shipped. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

Shipped a stale/broken split reconciliation verb, a per-tree executor regeneration after script-set-changing rebases, and all three D4 prompt/log fixes. **But the round-1 fix meant to make `executor_regenerated` disk-derived rather than exit-code-derived checks only PRESENCE in the executor slot** — and `prepare_execute` always guarantees an executor is present in a real worktree, so a generation that wrote nothing is reported as a successful refresh over the stale bytes it failed to replace.

## Premise verdict

**D0's premise did not hold**: it expected at least one of the four claims to be already closed, and all four were confirmed still live at HEAD. The one genuine refutation was narrower — "nothing compares the frozen manifest against live config" was half-wrong (a one-directional hard-abort comparison already existed), which materially reshaped D2 from *replace the guard* into *narrow the guard*.

## Gaps carried out of this landing

**16 total — 1 high, 5 medium, 10 low.** High: G15.

- **G15 (high) is a population-always-satisfies guard**: the success verdict is a presence check that the population can never fail.
- ⛔ **D2 has NEVER been exercised end to end** — self-declared and confirmed. This plan's own finalize ran under the OLD frozen manifest (the self-exercisability trap), and the `doc/plans/` lane never executes phase-6-finalize at all. **Exactly one call site exists in the tree and no run has reached it.**
- Two undocumented D2 scope limits: reconciliation is structurally blind to external (`project:`) steps, and backfill bypasses every composer pre-filter and lane-resolution pass.

## Inconsistencies found, and what was verified

- Report's build-gate enumeration said "4 Python files changed" | verified with `git show --numstat` | **verdict: 9 `.py` paths** — recorded before a later fix round and never re-derived.
- Report's D5 table annotated "15/6/7 tests" | verified with a `def test_` count on the delivered files | **verdict: 19/10/8** — stale pre-fix snapshots reading as final counts.

## Residue

D2's observation point is owed by construction.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-038 --status shipped`
- [x] row `pr` stamped `1236` — `orchestrator queue --set-row PLAN-CIS-038 --field pr --value 1236`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-038 --field landing --value landings/PLAN-CIS-038.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

⭐ **The first local plan to reach phase-6-finalize Step 1.5 is D2's real test** — record that as a watch, because it will be exercised for free by the next ordinary plan. G15 routes to **PLAN-CIS-052** (`540`).
