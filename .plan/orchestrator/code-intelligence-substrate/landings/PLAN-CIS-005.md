# Landing Analysis: PLAN-CIS-005 — Resolver configuration

epic: code-intelligence-substrate
workstream: WS-02
pr: 1252
merge_commit: `c0b4f3e8e`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/220-resolver-configuration/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 5 of 5 deliverables shipped. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

The menu, config section, working default and dead-ignore-rule retirement all landed and are mutation-proven. But with every resolver disabled, `capabilities` reports `module_edges: not_derivable` on a project whose `graph` verb still returns real declared edges — self-contradicting the handler's own docstring, and reachable one menu click away.

## Premise verdict

Two plan-stated hypotheses were explicitly tested and **correctly refuted by the run itself** (file-pattern is not the binding key — resolver id is; a precedence knob would be dead config given union semantics, so it was documented rather than shipped). Both refutations are declared and defensible, not gaps.

## Gaps carried out of this landing

**10 total — 1 high, 3 medium, 6 low.** High: G1.

- ⛔ **A SHIPPED TEST asserts the G1 defect as correct behaviour** (`test_capabilities_reports_not_derivable_when_every_resolver_is_disabled`). This is why four verification rounds missed it. **When G1 is fixed the test must be re-scoped, never simply deleted.**
- This is the **third sighting** of the *cannot-derive vs derived-nothing* archetype in this epic (PLAN-CIS-041 -> PLAN-CIS-002 -> here).
- Six anti-vacuity doc tables plus two code docstrings all need the same one-sentence caveat (G3, 8 sites).

## Inconsistencies found, and what was verified

- A shipped test comment claims "a developer's local binding would redden this suite" | verified by re-running with a hostile store injected against `test/conftest.py`'s autouse `PLAN_BASE_DIR` sandbox | **verdict: false** — the autouse fixture makes it structurally impossible. The same false rationale appears in the report.

## Residue

The configuration menu's Page 4 is now full — the next entry needs a Page 5, mechanically. `run-config-standard.md`'s "Full Example" omits five documented sections. A claimed pre-existing 38-failure pytest pollution mode does **not** reproduce (unconfirmed, not disproved).

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-005 --status shipped`
- [x] row `pr` stamped `1252` — `orchestrator queue --set-row PLAN-CIS-005 --field pr --value 1252`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-005 --field landing --value landings/PLAN-CIS-005.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G1 routes to **PLAN-CIS-053** (`550`, test-suite anti-vacuity) because the fix must move a shipped test that pins the defect — that is `550`'s exact charter.
