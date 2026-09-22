# Landing Analysis: PLAN-CIS-010 — Finalize dispatch evidence is missing

epic: code-intelligence-substrate
workstream: WS-04
pr: 1225
merge_commit: `c93431f88`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/170-finalize-dispatch-evidence-is-missing/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 5 of 5 deliverables shipped, but D1 and D3 fall short of their literal Done-when. Independent post-run audit verdict: **PARTIAL**.

Built a genuinely new deterministic, testable dispatch-audit detector — the prior LLM-only prose aspect could never fail — with a `not_evaluated` guard proven load-bearing by mutation. **But `channel_completeness` mixes an all-caller numerator against finalize-only denominators** (reporting `confidence: nominal` on a plan with zero finalize dispatch lines), the aggregate `counts` block still emits bare zeros in the exact never-evaluated case D1 was written to stop, and the D2 discriminator's `ran_inline` bucket is a fall-through default rather than a measurement.

## Premise verdict

Confirmed, with one half refuted by construction. D0 correctly re-grounded the vocabulary gap — but that is the **sibling** plan's premise (PLAN-CIS-035); this plan is scoped to the detector/consumer side only.

## Gaps carried out of this landing

**15 total — 5 high, 4 medium, 6 low.** High: G1, G2, G3, G7, G13.

- ⛔ **G13 is the worst gap in batch E**: the token-record discriminator cannot distinguish *measured zero* from *never measured*, so the headline `missing_dispatch_emission` finding is **structurally blind to exactly the failure it exists to catch.**
- **This plan has the highest high-severity count of any in the ingest (5).**
- G1/G2: channel completeness compares two incommensurable populations and has no not-evaluated state.

## Inconsistencies found, and what was verified

- None — this is the consumer half of the 170/180 split and it stayed inside that boundary. ✅ **Standing question answered: the split was respected.** No `_cmd_effort.py` or `phase-6-finalize/` file was touched, confirmed against the landed diff.

## Residue

The dispatch-line emission arm was correctly left to the sibling plan and was consumed there.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-010 --status shipped`
- [x] row `pr` stamped `1225` — `orchestrator queue --set-row PLAN-CIS-010 --field pr --value 1225`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-010 --field landing --value landings/PLAN-CIS-010.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

All five high gaps route to **PLAN-CIS-052** (`540`) — it is the finalize-dispatch observability plan and this is its densest input.
