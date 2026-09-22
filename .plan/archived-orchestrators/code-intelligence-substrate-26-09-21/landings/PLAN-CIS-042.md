# Landing Analysis: PLAN-CIS-042 — Attribution populations and the cost decomposition

epic: code-intelligence-substrate
workstream: WS-04
pr: 1154
merge_commit: `18ddd543c`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/030-attribution-populations-and-the-cost-decomposition/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 4 of 4 deliverables shipped. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

All four deliverables — the unattributed-population split, the `cache_read` attribution mechanism read and documented, the read-cost decomposition persisted, and the three-state schema read — shipped and are mutation-tested. But **the producer's own declared source-of-truth contract still states the refuted, un-subtracted attribution model.**

## Premise verdict

Confirmed — the "unattributed" catch-all identity is real and communicates falsely as attribution, and the fix is sound. The two high gaps are that the fix's rationale is undocumented **at its own authoritative surface**: `contract.md` and the `runtime_base.py` docstring both still assert a model that fails the reference suite when implemented literally.

## Gaps carried out of this landing

**10 total — 2 high, 3 medium, 5 low.** High: G1, G2.

- **G1/G2 (high): the declared source of truth contradicts the shipped code.** A reader who follows the contract implements the refuted model.
- ⛔ **A second `cache_read_per_tool_use` emitter now exists** (plan-retrospective, PR #1260) over a **different population**, violating this plan's own one-writer rule (G3). The two are not comparable and neither document cross-references the other — a name collision that will produce a false comparison.

## Inconsistencies found, and what was verified

- None beyond the audit's own. PR merge corroborated: `git log --grep="#1154"` -> `18ddd543c`.

## Residue

D2's and D3's magnitude claims remain corpus-blocked and were explicitly declared as residue rather than published as fact — correct behaviour.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-042 --status shipped`
- [x] row `pr` stamped `1154` — `orchestrator queue --set-row PLAN-CIS-042 --field pr --value 1154`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-042 --field landing --value landings/PLAN-CIS-042.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G1/G2 route to **PLAN-CIS-050** (`520`). G3 (the colliding field name) needs a rename or an explicit cross-reference and routes there too.
