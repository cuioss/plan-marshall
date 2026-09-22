# Landing Analysis: PLAN-CIS-015 — Outline plan-scope derivation integrity

epic: code-intelligence-substrate
workstream: WS-05
pr: 1283
merge_commit: `aeab5ab`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/280-outline-plan-scope-derivation-integrity/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — Arm B shipped in full; Arm A split off to PLAN-CIS-047 per the plan's own mandate. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

Arm B shipped correctly and mutation-proven: the published `worktree_state` discriminator has one owner with six branching consumers, and outline classification now derives from the write-set rather than from narrative intent. **Arm A (closure) was split off to PLAN-CIS-047 per the plan's own split mandate — but the run report never discloses this**, a pure traceability defect, since the split itself is contract-conformant.

## Premise verdict

Confirmed — every one of the plan's D0 claim-table rows was re-derived and held. Both mandatory split-guard arms were correctly separated by failure signature.

## Gaps carried out of this landing

**13 total — 0 high, 9 medium, 4 low.** No high-severity entries.

- ⭐ **The sharpest self-catch in the ingest**: the verification sub-agent found that the shipped bucket-adjudication check **had itself become a second, weaker classifier competing with the aggregator — the very defect the check exists to catch** — and it was blocking valid outlines. Caught before merge and narrowed to the one provable direction.
- **G3: the D5 corpus-completeness claim is FALSE.** Two sites in the swept population were never converted and never declared as exclusions — a corpus claiming completeness that is not complete.
- **G10: a whole normative clause has zero implementation.**

## Inconsistencies found, and what was verified

- Report never mentions the D2/D3 split to PLAN-CIS-047 — the strings do not appear in it | verified by content search of the report | **verdict: confirmed traceability defect**, not a contract violation.

## Residue

Two stubs in a sibling bundle's test still return the retired boolean shape; six stale "pre-materialization" documentation surfaces survive the run's own sweep, one inside a file the run itself edited.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-015 --status shipped`
- [x] row `pr` stamped `1283` — `orchestrator queue --set-row PLAN-CIS-015 --field pr --value 1283`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-015 --field landing --value landings/PLAN-CIS-015.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

⚠ **Ownership ambiguity to settle**: the two stray stubs in `test_freshness_notation_crosscheck.py` are owned by neither this plan's nor PLAN-CIS-017's Expected Surface, and it was this plan's audit that found them. Assign them to **PLAN-CIS-053** (`550`), which sweeps test vacuity fleet-wide.
