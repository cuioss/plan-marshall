# Landing Analysis: PLAN-CIS-037 — Dispatch-boundary ledger is not a commensurable population

epic: code-intelligence-substrate
workstream: WS-04
pr: 1173
merge_commit: `3f64b7186`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/060-dispatch-boundary-ledger-is-not-a-commensurable-population/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 5 of 5 deliverables shipped. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

The ledger population is now source-derived (9 classes / 3 register / 6 excluded) and an over-covering ratio is refused the reconciliation maximum. **But the coverage verdict is gated on a truthy boundary sum, so it renders nothing at all — no bullet, no FAILURE — for any phase whose boundary rows are all-zero**, which is precisely the row the code's own comment says the row-count field exists to make legible.

## Premise verdict

Confirmed, not refuted. All three plan-claimed symptoms were real. **D1's own hypothesised fork was correctly tested and refuted by the run itself**: the class omission drives *under*-coverage while the impossible ratio is *over*-coverage from a separate accumulate-vs-window cause — exactly the check the plan instructed the run to make first.

## Gaps carried out of this landing

**9 total — 3 high, 3 medium, 3 low.** High: G1, G2, G3.

⛔⛔ **THE LEDGER'S PREMISE ABOUT THIS PLAN WAS WRONG AND IS CORRECTED HERE.** The prior anchor believed this plan halted at a D1 gate, citing commit `c586d2cbe` / PR #1150. **That commit belongs to a different epic** — `truthful-signals`' plan `060-invented-plan-scoping-flags-are-an-overgeneralized-convention`. It is a **cross-epic numbering collision on the bare numeral `060`.** This plan never halted: it completed and merged as PR #1173.

- **STANDING RULE ADDED:** a bare `NNN-` export number is NOT unique across epics. Corroborate a commit against the epic named in its message before attributing it.
- D2 and D4 both need a follow-up pass before the boundary-ledger figures can be trusted for share-of-spend arithmetic.

## Inconsistencies found, and what was verified

- The ledger's own standing question cited `c586d2cbe`/#1150 as this plan's halt | verified with `git show --stat c586d2cbe` | **verdict: different epic, different plan** — see above.

## Residue

None declared as owed by the run. The audit found D2's zero-sum gating gap and D4's same-population-unreachable gap as unshipped follow-on work, none of it acknowledged in the report.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-037 --status shipped`
- [x] row `pr` stamped `1173` — `orchestrator queue --set-row PLAN-CIS-037 --field pr --value 1173`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-037 --field landing --value landings/PLAN-CIS-037.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

All three high gaps route to **PLAN-CIS-050** (`520`).
