# Landing Analysis: PLAN-CIS-036 — Exploration split measured on one phase, and it is the worst case

epic: code-intelligence-substrate
workstream: WS-04
pr: 1178
merge_commit: `dd0b70b10`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**blocked** — 0 of 5 deliverables — halted at D0. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

Correctly halted at D0 on the same corpus-unreachable finding as PLAN-CIS-039 — **but the report's central hand-off claim is false.** "Nothing needs building, only the corpus needs to be present" is stated in four places and is wrong. **This is the plan that owns the epic's headline figures.**

## Premise verdict

D0's halt is unconditionally correct. **REFUTED: the report's own justification for it.** No split-reporting instrument exists anywhere in the retrospective auditor — no check reads the three exploration sub-source fields that *define* D1's split, and the closest existing check pools all six phases into one figure, which D1 explicitly forbids. **That missing aggregator is git-derivable and could have been built in the cloud clone with no corpus at all.**

## Gaps carried out of this landing

**7 total — 0 high, 5 medium, 2 low.** No high-severity entries.

- ⛔⛔ **The epic's headline figures remain n=1 and are now known to be un-derivable with the instruments that exist.** index-answerable 15.9% / doc-residency 65.2% / exploration ~77% were never re-derived, and the tool that would derive them was never built.
- ⛔ **Do not resume this plan on its own residue text** — it would send a session to rebuild what the report wrongly says already exists. The aggregator (G3/G4/G7) must be built first, and it needs no corpus.
- The lane contract has no rule for what a run blocked on an environment prerequisite must produce — both this plan and PLAN-CIS-039 independently inferred the same correct behaviour from first principles (G6).

## Inconsistencies found, and what was verified

- Report claims "nothing needs building" while its own D1 justification asserts the split instrument "already exists" | verified by content search for `index_answerable` / `doc_residency` under the auditor skill -> **0 matches**, against a control of 33 matches elsewhere | **verdict: the instrument does not exist; the hand-off is false.** D0's halt itself is unaffected.

## Residue

D1-D4 entirely unattempted; no `report-02.md`; no sibling plan closes the residue.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-036 --status shipped`
- [x] row `pr` stamped `1178` — `orchestrator queue --set-row PLAN-CIS-036 --field pr --value 1178`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-036 --field landing --value landings/PLAN-CIS-036.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

⛔ **Split this plan.** The git-derivable half (build the per-phase sub-source aggregator) can run **now, locally, with no corpus** and is a prerequisite for the measurement half. Staged as a new spec — see `epic.md` § Open Decisions.
