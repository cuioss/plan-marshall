# Landing Analysis: PLAN-CIS-022 — Token ledgers disagree, and the smallest is named actual

epic: code-intelligence-substrate
workstream: WS-04
pr: 1293
merge_commit: `85abeeb96`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/340-token-ledgers-disagree-and-the-smallest-is-named-actual/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 7 of 7 deliverables shipped. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

All seven deliverables shipped, with five load-bearing guards driven red under mutation. D1's writer-side re-derivation **refutes the plan's own load-bearing premise more sharply than expected** — the recalibration key has **no producer anywhere, ever** — making the defect latent by construction rather than by accident. The new reconciliation verb has **no caller anywhere in the workflow.**

## Premise verdict

D1 (the hard gate) confirmed that the three ledgers' populations differ by construction. It also **refutes the plan's stated rationale** ("actual compared against whole-plan prediction, latent only because the observed run lacked a prediction"): the comparand key has literally no producer in the tree, so no run has ever carried a prediction and no recalibration table was ever corrupted. D2's fix keeps its value but loses its original rationale.

## Gaps carried out of this landing

**11 total — 0 high, 4 medium, 7 low.** No high-severity entries.

- ⛔ **`reconcile-ledgers` has zero workflow call sites** (G4) — the plan's Goal is reached only in principle. A `RecursionError` cliff at ~1000 same-timestamp rows per phase (G3) is contained *only* by the fact that nothing calls it.
- D3's own Done-when (every rendered figure has a persisted counterpart) was verified **only in the forward direction** (store -> render). The reverse walk — the plan's literal requirement — was never performed (G11).
- The three-ledger arithmetic totals remain **unverifiable**: the corpus was absent in both the run's clone and the audit's clone, independently confirmed rather than assumed.

## Inconsistencies found, and what was verified

- None beyond the audit's own extensive self-correction. Note the audit's **first pass filed a false gap** on `pair_rows` maximality which was retracted on adversarial review — evidence the adversarial pass is doing real work. PR merge corroborated: `git log --grep="#1293"` -> `85abeeb96`.

## Residue

Wiring the verb into a workflow, and the reverse-direction verification, both need a real corpus — available locally, not in a cloud clone.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-022 --status shipped`
- [x] row `pr` stamped `1293` — `orchestrator queue --set-row PLAN-CIS-022 --field pr --value 1293`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-022 --field landing --value landings/PLAN-CIS-022.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

Routes to **PLAN-CIS-050** (`520`). ⭐ **This plan is now cheaply completable locally** — the corpus it needed is on this machine.
