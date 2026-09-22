# Landing Analysis: PLAN-CIS-040 — Envelope length and the isolation currency

epic: code-intelligence-substrate
workstream: WS-06
pr: 1185
merge_commit: `6f1cb7b12`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/090-envelope-length-and-the-isolation-currency/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**partial** — 2 of 5 deliverables shipped; 3 blocked. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

D0 correctly resolved that D2 was shippable without a corpus, and D2 — restating `token-management.adoc` §6 in billing-weight / turns-resident currency — shipped and passed a cold read. D1, D3 and D4 (the actual per-phase measurement, the creation/read inversion mechanism, and an envelope-length lever) remain fully blocked with **nothing staged to resume them**. The report self-labels "completed".

## Premise verdict

Confirmed that isolation-as-biggest-lever survives the currency correction (the recommendation was kept verbatim and passed a cold read). **But the fix introduced its own unsourced quantitative claim** — "bounded and small", with no population (G8): the exact archetype the plan exists to remove, recurring one level down inside its own correction.

## Gaps carried out of this landing

**10 total — 0 high, 6 medium, 4 low.** No high-severity entries.

- ⛔ **This plan is the correct model for a corpus-blocked run**: it separated the git-derivable half and shipped it, instead of halting wholesale. PLAN-CIS-036 and PLAN-CIS-039 did not, and that difference is worth generalising into the lane contract.
- §6's numeric figures were correctly **deleted rather than restated** — but a duplicate unsourced ~10-15K figure survives untouched in a different section (G2), and a companion ~5-10 dispatches figure survives unswept (G3).
- The mandatory SVG rasterise-and-read-back verification was never performed, and the lane contract has no routing row pointing a run at that skill (G4/G5).

## Inconsistencies found, and what was verified

- Report claimed the SVG `<title>` was "re-cast to residency" alongside `<desc>` | verified with `git show 6f1cb7b -- doc/resources/diagrams/context-isolation.svg` | **verdict: only `<desc>` was rewritten**; `<title>` still carries the pre-correction framing (promoted to G10).

## Residue

D1/D3/D4 blocked on the same unreachable corpus, with nothing staged anywhere to resume them.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-040 --status shipped`
- [x] row `pr` stamped `1185` — `orchestrator queue --set-row PLAN-CIS-040 --field pr --value 1185`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-040 --field landing --value landings/PLAN-CIS-040.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

The blocked deliverables now have a home: they depend on the same aggregator PLAN-CIS-036 needs. Sequence behind it. G8/G10 route to **PLAN-CIS-054** (`560`).
