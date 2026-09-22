# Landing Analysis: PLAN-CIS-012 — Footprint read outside its window

epic: code-intelligence-substrate
workstream: WS-04
pr: 1268
merge_commit: `d34f2b8`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/250-footprint-read-outside-its-window/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 4 of 6 deliverables confirmed. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

The three-state footprint reader (unknown vs empty) and the fail-closed composer both shipped and are non-vacuously tested — all ten audit mutations were killed. **But the plan's own defect class survives, high-severity, in the file it changed**: `verify_failure_scope` still diffs a foreign checkout, and can invert an unmeasurable footprint into the single most confident classifier verdict, whenever a plan's worktree is pending.

## Premise verdict

Confirmed for D2-D6. **Refuted for the completeness of the fix**: the review-driven removal of the `Path.cwd()` fallback closed only one route into the same wrong answer; `worktree_path`'s documented fallback to the main checkout (reached via `has_worktree: False`) reopens it.

## Gaps carried out of this landing

**7 total — 1 high, 4 medium, 2 low.** High: G1.

- ⛔ **G1 (high) is the epic's signature "confident verdict over an unexamined case" recurring inside a plan built to eliminate exactly that.** A clean checkout with a pending worktree reads as a MEASURED empty footprint, and drives phase-5-execute's default "Stash foreign files" recommendation on no evidence.
- **G6 explains why twelve verification rounds and a mutation sweep all missed it**: the guarding test's name and docstring promise a broader guarantee than the test covers — it stubs only the `WorktreeResolutionError` route and leaves the `pending` route (the one G1 exploits) untested.

## Inconsistencies found, and what was verified

- D1's published population omitted a 12th truthiness-predicate hit (`_manifest_validation.check_build_verdict_consistent`) | verified by an independent predicate sweep returning 12 against 11 published | **verdict: benign in direction** (an unresolvable footprint disables the assertion rather than grading a false pass) **but an inconsistency in a deliverable whose whole contract is a complete derived population.**

## Residue

D3 (reduce the largest lever) was deliberately not owned here — split by cross-epic agreement. `plan-retrospective`'s undeclared `reads:[worktree]` stays deliberately unfixed: declaring it today would make the step violate the ordering rule it exists to enable.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-012 --status shipped`
- [x] row `pr` stamped `1268` — `orchestrator queue --set-row PLAN-CIS-012 --field pr --value 1268`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-012 --field landing --value landings/PLAN-CIS-012.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G1 routes to **PLAN-CIS-050** (`520`); G6 routes to **PLAN-CIS-053** (`550`). ⭐ The phantom two-field declaration form this plan left as residue was **independently closed by PLAN-CIS-047** (`350`).
