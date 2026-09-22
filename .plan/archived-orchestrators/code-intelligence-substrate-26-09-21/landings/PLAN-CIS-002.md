# Landing Analysis: PLAN-CIS-002 — LSP-shaped query API

epic: code-intelligence-substrate
workstream: WS-02
pr: 1207
merge_commit: `8d5055f82`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/130-lsp-shaped-query-api/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 4 of 5 deliverables confirmed; D1 deliberately retired by a sibling plan. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

The `capabilities` verb and the search measurement contract shipped and are non-vacuous, but `content_search` still cannot distinguish *never crawled* from *crawled, found nothing* — the exact ambiguity D2 exists to close, left unresolved on one of its own three rows.

## Premise verdict

D2-D5's premises held. **D1 (the `lsp` facade) was confirmed at merge and then deliberately RETIRED** by sibling plan `135` (PR #1214). Its absence from the tree is the intended state, not a regression — do not re-flag it.

## Gaps carried out of this landing

**9 total — 0 high, 4 medium, 5 low.** No high-severity entries.

- `capabilities.content_search` still conflates *cannot derive* with *derived nothing* (G1, medium). **This is the same archetype as PLAN-CIS-005's G1 and the coverage defect in PLAN-CIS-041** — three sightings across one epic, each inside a fix meant to remove it.
- D2's "verify inside a dispatched leaf with Grep/Glob revoked" constraint was **never discharged**, by this plan or any later one (G7). It is epic-wide unmet.

## Inconsistencies found, and what was verified

- Report claimed D2 is "per-call (uncached)" | verified by two `cmd_capabilities` calls in one process | **verdict: refuted** — `path_attribution` is memoized for the process lifetime (`_PATH_CLAIM_CACHE`), contradicting three shipped documents.
- Report's contract check said "six commits" | verified against the PR | **verdict: eight**.

## Residue

Nine gaps open. The leaf-verification obligation (G7) has no owner anywhere in the epic.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-002 --status shipped`
- [x] row `pr` stamped `1207` — `orchestrator queue --set-row PLAN-CIS-002 --field pr --value 1207`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-002 --field landing --value landings/PLAN-CIS-002.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G1 folds into the cross-cutting *cannot-derive vs derived-nothing* item recorded in `epic.md` § Open Defects. G7 needs an owner — it is not covered by any staged `5xx` plan.
