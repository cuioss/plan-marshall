# Landing Analysis: PLAN-CIS-034 — Post-run band contract and ordering residue

epic: code-intelligence-substrate
workstream: WS-04
pr: 1175
merge_commit: `0e7f644`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/050-post-run-band-contract-and-ordering-residue/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 3 of 5 deliverables confirmed. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

The split-band contract, the edge-derivation gate, the accumulator fold and the five-tier footprint resolver all shipped correctly — but **the gate's own coverage canary went blind one day later**, and D4's "two consumers recover together" claim is dead in the shipped workflow (it documents a `--diff-file` no step produces).

## Premise verdict

Confirmed for D2/D3/D5. **Refuted for D1's own coverage claim**: the canary built to force re-measurement when consumer-side vocabulary widened stayed GREEN when exactly that happened — a sibling plan added `destroys` on two steps one day later, and `_ABSENT_CONSUMER_MARKERS` never included that spelling.

## Gaps carried out of this landing

**10 total — 1 high, 7 medium, 2 low.** High: G1.

- ⛔ **G10 is the epic's signature defect recurring inside the very gate this plan shipped to prevent it** — a guard that could not fire, which then demonstrably failed to fire on the real event, one day after landing.
- G1 (high): D4's footprint recovery is wired in the script but unreachable through the documented `SKILL.md` invocation (a phantom `work/footprint.txt`).
- Two registry-consumer doc defects name a resolver relationship that does not exist, and rest on a retired key.

## Inconsistencies found, and what was verified

- Report's published D1 cardinality "13 edges / 24 steps (~54%)" | verified by re-running `derive_ordering_edges()` against the live tree | **verdict: 14 / 25 (56%)** — the figure was true when written; the drift is real, **and the canary meant to detect the drift-triggering event did not fire.**

## Residue

Merge-commit-SHA-on-enqueued-path and analyze-logs' divergent tier-1 fail-through policy are both open by explicit design, not defects.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-034 --status shipped`
- [x] row `pr` stamped `1175` — `orchestrator queue --set-row PLAN-CIS-034 --field pr --value 1175`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-034 --field landing --value landings/PLAN-CIS-034.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G10 routes to **PLAN-CIS-053** (`550`) — it is the canonical anti-vacuity target. G1 routes to **PLAN-CIS-052** (`540`).
