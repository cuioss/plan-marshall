# Landing Analysis: PLAN-CIS-016 — Auditor detector integrity

epic: code-intelligence-substrate
workstream: WS-05
pr: 1276
merge_commit: `7951ada`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/290-auditor-detector-integrity/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 5 of 6 deliverables confirmed; merge-gate condition 2 operator-overridden. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

All six named failure modes were confirmed at HEAD and closed with mutation-proven fixes. **But the census — the deliverable built specifically to detect vacuous and unfireable detectors — shipped with its own documented precedence rule that provably never fires on the live emitter set**, and one of its guards is unpinned by all 640 tests in its own suite directory.

## Premise verdict

Confirmed on all six members, **with one important refutation the run made itself**: the "zero production emitters" claim for the `[LOCK]` marker was confirmed as a real defect but **refuted as to cause** — production does interpolate the string via `log_lock_event` (10 call sites). The real defect was a path mismatch (`.plan/logs/` written vs `.plan/local/logs/` scanned), which D3 fixed by scanning both roots and reporting `unmeasured` rather than a fabricated zero.

## Gaps carried out of this landing

**17 total — 1 high, 9 medium, 7 low.** High: G1.

⛔⛔ **THE LEDGER'S ITEM-B PREMISE IS CORRECTED HERE.** The prior anchor recorded that the `[LOCK]` marker had *zero production emitters, so the detector AND its green test suite are both vacuous*. **That diagnosis was substantively refuted**: the emitter and its tests were genuinely real; the defect was the scan-root path mismatch, and **it IS closed** — non-vacuous, mutation-proven, tests re-pointed at the production emitter.

- ⛔ **But the vacuous-guard archetype was reproduced inside the fix's own flagship deliverable** (G1, high): D6's documented precedence rule cannot fire on ANY of the 12 live emissions — not a latent risk, *a rule that cannot fire today*.
- The census does not census itself (mode E) — documented by design, not resolved.

## Inconsistencies found, and what was verified

- Ledger premise that item B's detector and suite were both vacuous | verified against the production emitter and its 10 call sites | **verdict: refuted as to cause; the real defect was a path mismatch, now closed.**

## Residue

A `frozen_manifest_stale` removal is still invisible to the reader — the same false mis-prune D5 was built to end, reachable by a live path. The withheld "warning fires at every boundary" claim was never located by either the run or the audit.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-016 --status shipped`
- [x] row `pr` stamped `1276` — `orchestrator queue --set-row PLAN-CIS-016 --field pr --value 1276`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-016 --field landing --value landings/PLAN-CIS-016.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G1 routes to **PLAN-CIS-051** (`530`); G3's unpinned guard to **PLAN-CIS-053** (`550`). ⚠ The unlocated C5 claim is recorded as an **open question**, carrying neither a verdict nor a mode.
