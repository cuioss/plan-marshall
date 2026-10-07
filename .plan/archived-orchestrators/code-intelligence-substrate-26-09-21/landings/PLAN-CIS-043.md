# Landing Analysis: PLAN-CIS-043 — Self-review surfacing integrity

epic: code-intelligence-substrate
workstream: WS-05
pr: 1189
merge_commit: `94bcddf`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/100-self-review-surfacing-integrity/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 2 of 5 deliverables shipped as specified. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

D1 (the shared resolver) and D2 (population-derived registry-to-check coverage over 17 entries, publishing its population size) both landed correct and mutation-proven. **D3, D4 and D5 shipped weaker mechanisms than specified**: D3 publishes scope but does not reject a scope-less absence claim; D4's guard is opt-in and the one stream that can carry plan-directed content is never told to use it; and D5's round-loop termination prose is unreachable from Step 4's actual execution path.

## Premise verdict

Confirmed. The detector file-set asymmetry was real and load-bearing, and two registry entries genuinely lacked a consuming check. **D3's asserted absence was refuted** — the scope tokens already existed — which the report correctly disclosed and used to reshape D3.

## Gaps carried out of this landing

**10 total — 0 high, 5 medium, 5 low.** No high-severity entries.

- ⛔ **D3 introduces the same shape it targets** (G8): a documented obligation to quote scope in an absence claim, with **no enforcing mechanism** — structurally the same defect as D2's original.
- ⛔ **D2's own population-size publication is swallowed by the repo's pytest addopts** (G6), so the plan's own *a population-derived detector must publish its size* clause **was not actually discharged on a green CI run.**
- **G7: the report mis-stated D2's population as 23 entries; it is 22** — the one section demonstrating D3's scope-discipline rule violated the accuracy that rule exists to protect.
- ⛔ **This plan owns F8** (a mid-run inbox message has no reader) via D4, and D4 shipped opt-in — so **F8 is NOT closed.**

## Inconsistencies found, and what was verified

- None beyond the audit's own; the D3 refutation was disclosed by the run rather than found later.

## Residue

D5's self-seeding classification was never wired into Step 4, so it never fires in practice. Step 4's remediation sentence still prescribes correct-and-re-run, contradicting D5's deletion-only rule.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-043 --status shipped`
- [x] row `pr` stamped `1189` — `orchestrator queue --set-row PLAN-CIS-043 --field pr --value 1189`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-043 --field landing --value landings/PLAN-CIS-043.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

⛔ **F8 remains open** and is re-recorded as an Open Defect. G6/G8 route to **PLAN-CIS-051** (`530`).
