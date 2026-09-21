# Landing Analysis: PLAN-CIS-046 — Remove the LSP query facade

epic: code-intelligence-substrate
workstream: WS-02
pr: 1214
merge_commit: `064b387ed`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/135-remove-lsp-query-facade/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 4 of 4 deliverables shipped. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

A clean, surgical removal with zero collateral. The audit then found four pre-existing doc-hygiene defects in the same query surface that this plan deferred and no later plan has closed — heading hierarchy misfiles **11 of 17** verb sections under the wrong H2 (not the 7 the run's own cold read disclosed), plus verb-set drift on `siblings` / `profiles` / `descriptor-regression-check`.

## Premise verdict

Not applicable — a targeted cleanup with no central hypothesis. The zero-adoption claim that justified removing the facade was **confirmed** by a whole-tree sweep that included the git-ignored `.plan/` tree.

## Gaps carried out of this landing

**15 total — 0 high, 7 medium, 8 low.** No high-severity entries.

- **This row did not exist in the ledger before this ingest.** It was authored mid-flight as an operator correction to PLAN-CIS-002 and has been assigned `PLAN-CIS-046` here.
- **The root cause of the recurring verb-set-vs-docs drift is a missing plugin-doctor rule** (G14). It is why the drift survived both PLAN-CIS-002 and this plan. Prioritise the detector over further one-off doc patches.

## Inconsistencies found, and what was verified

- Report's contract check claimed "every commit carries the Co-Authored-By trailer" | verified against the PR's commit list | **verdict: 1 of 5 lacks it** (the plan-authoring commit, which predates the run session).
- Report quoted a review bot at "107 minutes" | verified against the comment body | **verdict: 103** — the comment was edited after the report was drafted.

## Residue

Four pre-existing doc-hygiene items (G3-G9) remain open. The `content_search` vocabulary item was deliberately left untouched here as out of scope.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-046 --status shipped`
- [x] row `pr` stamped `1214` — `orchestrator queue --set-row PLAN-CIS-046 --field pr --value 1214`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-046 --field landing --value landings/PLAN-CIS-046.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G14 (the missing detector) is the highest-leverage item and belongs with the `560` documentation-truthfulness wave. The doc-hygiene items route to **PLAN-CIS-054** (`560`).
