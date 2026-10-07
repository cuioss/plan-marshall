# Landing Analysis: PLAN-CIS-014 — Aggregate cost invisible to the per-call ceiling

epic: code-intelligence-substrate
workstream: WS-04
pr: 1260
merge_commit: `89edc991`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/270-aggregate-cost-invisible-to-per-call-ceiling/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 4 of 6 deliverables confirmed. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

The per-plan and cross-plan cumulative cost roll-ups shipped correctly, as an addition beside the unchanged per-call ceiling, and the numeric-reduction half is honestly blocked on an unreachable archived-plan corpus per the plan's own fallback. **But the shipped roll-up carries two high-severity defects that make it misreport precisely the many-fast-calls class it was built to surface.**

## Premise verdict

Confirmed that a per-call ceiling is structurally incapable of surfacing a dominant-but-fast script, and that D1's wall-clock share is a **latency** finding, structurally unconvertible to a billing figure because no join key exists. **Refuted on the deliverable's own ground**: the new roll-up's published denominator rounds to `0.0s` for a sub-second corpus, and its per-plan reader has no line-shape guard, so a failed script's captured stdout can manufacture a call that never ran.

## Gaps carried out of this landing

**14 total — 2 high, 5 medium, 7 low.** High: G1, G14.

- ⛔ **G1 + G14 are a self-referential recurrence of the epic's own theme**: the instrument built to fix *a confident wrong signal hides a caveat* ships with its own instance of exactly that.
- **G3 shows why it survived**: the guarding test uses round numbers (30.0s / 10.0s) that reconcile identically at both one and three decimal places, so it is structurally unable to catch the rounding defect it exists to guard. Mutating the fix candidate leaves the whole 640-test suite green.
- D1's structural currency finding (wall-clock is not billing; no join key) is **durable** and is carried into shipped code and docs at four sites, not merely the report.

## Inconsistencies found, and what was verified

- Report's "37 test functions added" | verified by an AST diff of the merged commit against its parent | **verdict: 43** — the figure was taken before post-report review-fix commits and never re-derived, **despite being labelled "re-derived at the moment of this claim".**

## Residue

D1(b), D3 and D4(b) — the actual reduction work — remain genuinely undischarged, blocked purely on corpus availability, with no successor plan naming the two hot paths. That is an epic-level infrastructure gap, not a defect of this plan.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-014 --status shipped`
- [x] row `pr` stamped `1260` — `orchestrator queue --set-row PLAN-CIS-014 --field pr --value 1260`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-014 --field landing --value landings/PLAN-CIS-014.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G1/G14 route to **PLAN-CIS-050** (`520`); G3 to **PLAN-CIS-053** (`550`). ⭐ **The blocked reduction half is now unblocked locally** — the archived-plan corpus is on this machine.
