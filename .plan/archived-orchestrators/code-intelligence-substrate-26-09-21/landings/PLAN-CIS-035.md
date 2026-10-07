# Landing Analysis: PLAN-CIS-035 — Dispatch spend on dispatches that produced nothing

epic: code-intelligence-substrate
workstream: WS-04
pr: 1180
merge_commit: `1565a29b9`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/070-dispatch-spend-on-dispatches-that-produced-nothing/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 5 of 5 deliverables shipped. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

Added the missing `returned_with_findings` taxonomy member and routed finalize loop-backs to it, so they are no longer mis-stamped `error`; settled the token-column gate through the pre-existing `unmeasured` infrastructure with no new writer; and correctly halted D3's corpus-gated measurement rather than fabricating a share. **But the newly published waste figures still sum a `total_tokens` column that silently defaults to `0` on an omitted flag** — mixing measured and fabricated spend in exactly the way D2 was supposed to have eliminated one column over.

## Premise verdict

**Refuted at D1, exactly as instructed.** The run confirmed *in the clone* — not from the forbidden machine-local record — that the taxonomy had no member for a findings-bearing return, and it did not quote the retired "a third of finalize spend" figure anywhere. ✅ **This answers a standing ledger question: the run honoured the refuted-premise correction and re-derived before scoping.**

## Gaps carried out of this landing

**13 total — 1 high, 7 medium, 5 low.** High: G1.

- **G1 (high): a fall-through `else: value = 0` on an omitted `--total-tokens` manufactures a measured zero**, and the two published waste figures sum that column.
- **G13 is a population-derivation violation the plan's own text warned against**: `_TERMINAL_WASTE_CAUSES` / `_RETRYABLE_CAUSES` are hand-written literals with no structural tie to the enum they partition. The run reproduced the archetype it was told to avoid.

## Inconsistencies found, and what was verified

- None material. The report's own D2 claim ("D5 reads `total_tokens`, not these columns") was the one substantive inaccuracy, and the audit corrected it in the gap entries.

## Residue

D3's finding-yield sweep and D4's class-shares measurement remain blocked on the archived-record corpus — explicitly deferred per the plan's own HALT instruction, not a shortfall.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-035 --status shipped`
- [x] row `pr` stamped `1180` — `orchestrator queue --set-row PLAN-CIS-035 --field pr --value 1180`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-035 --field landing --value landings/PLAN-CIS-035.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G1/G13 route to **PLAN-CIS-050** (`520`). ⭐ **D3/D4 are now unblocked locally** — the corpus is on this machine.
