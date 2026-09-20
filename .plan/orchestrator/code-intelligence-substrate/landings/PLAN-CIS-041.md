# Landing Analysis: PLAN-CIS-041 — LSP in phase-5-execute: opt-in lookup and verified write

epic: code-intelligence-substrate
workstream: WS-03
pr: 1140
merge_commit: `cc5bd8bac`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/010-lsp-in-execute-lookup-and-write/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 5 of 5 deliverables shipped. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

`lsp-client` ships and works against a real pyright, but D2's rollback guard fails OPEN on a slow or silent server, and the workspace-symbol / document-symbol answers are unusable — no file path on workspace-symbol, and document-symbol returned 1 of 43 symbols because nested children are dropped.

## Premise verdict

D0 confirmed (warm server reachable, boot is cheap) **but the latency table the hosting decision rested on was warm-path only**. Re-measured cold, 2 of the 4 verbs cost ~1-2.5 s per call, not the millisecond figures quoted. The operator decision that this surface is strictly opt-in stands and is unaffected; the cost basis under it does not.

## Gaps carried out of this landing

**16 total — 4 high, 7 medium, 5 low.** High: G1, G2, G13, G15.

- **The central safety rule fails open.** D2's diagnostics-worsened guard was reproduced failing on a slow/silent server end-to-end through the shipped edit verb — not by a synthetic probe (G2/G13, high, one fix window).
- **The verdict guard compares an aggregate error COUNT, not a per-file SET**, so a moved or swapped error passes as success (G15, high; same fix window as G2/G13).
- **Two verbs return silently incomplete answers** (G1/G5) — the exact archetype this epic exists to remove, shipped by the plan that introduces the surface.

## Inconsistencies found, and what was verified

- D0's latency table presented warm-path figures as the per-call cost basis for the hosting decision | verified by re-measurement across three sessions | **verdict: warm-path only**; true cold cost is ~1-2.5 s on 2 of 4 verbs.
- Report claimed "35 passed in the lsp-client suite" | verified by pytest re-run at HEAD | **verdict: 36** — one test was added after the report was written.

## Residue

16 gaps open, none fixed post-merge. Reviewer coverage was **1 of 3** — two bots were rate-limited and no re-review was obtained, so this landing carries less external review than its size warrants.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-041 --status shipped`
- [x] row `pr` stamped `1140` — `orchestrator queue --set-row PLAN-CIS-041 --field pr --value 1140`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-041 --field landing --value landings/PLAN-CIS-041.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

All 16 gaps route to **PLAN-CIS-048** (`500`, already run) and the staged `5xx` wave. The cold-latency correction must not be re-derived — it is settled here.
