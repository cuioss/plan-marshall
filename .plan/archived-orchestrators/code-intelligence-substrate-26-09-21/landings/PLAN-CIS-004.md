# Landing Analysis: PLAN-CIS-004 — Native coordinate resolvers

epic: code-intelligence-substrate
workstream: WS-02
pr: 1238
merge_commit: `87c71d3f8`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/210-native-coordinate-resolvers/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 6 of 6 deliverables shipped. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

The Python and npm derivation resolvers work exactly as specified — mutation-proven, and two fresh external-repo clones reproduced D0's headline measurements exactly. But **the discoverers feeding them cannot see a Poetry-managed or setuptools Python project at all**, and both misreport it as `status: ok, edge_count: 0` rather than as a missing capability.

## Premise verdict

Confirmed — but the "majority of unresolved rows fall into the three named classes" hypothesis held only barely at **52.1%**, and only when Maven meta-syntax is counted as a documentation placeholder.

## Gaps carried out of this landing

**11 total — 2 high, 7 medium, 2 low.** High: G1, G10.

- **Poetry and setuptools projects get a silently empty graph reported as success** (G1/G10, both high) — the same failure class the whole epic exists to eliminate, recurring one layer down from a plan that had just fixed the layer above.
- All five gaps trace to **one chokepoint function**, `_parse_pyproject_metadata` — a single fix window.
- Two PEP 508 spellings (`name@url`, `name;marker`) silently lose the edge with no note (G2/G3).

## Inconsistencies found, and what was verified

- Report's build-gate file count said "10 files" | verified with `git show --name-only` on the squash commit | **verdict: 13** — the exact stale-figure defect present inside the report that proposes fixing stale figures.

## Residue

Gradle's `project:name` form derives no edge (deliberately unfixed, now pinned by a test); Python discovery reads only the dev extra (disclosed); a scoped npm module cannot round-trip through `save_module_derived` (characterised, not fixed).

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-004 --status shipped`
- [x] row `pr` stamped `1238` — `orchestrator queue --set-row PLAN-CIS-004 --field pr --value 1238`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-004 --field landing --value landings/PLAN-CIS-004.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G1/G10 route to **PLAN-CIS-049** (`510`). The one-chokepoint finding makes this cheap — schedule it as a single window.
