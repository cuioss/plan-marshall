# Landing Analysis: PLAN-CIS-024 — Documentation surface provider

epic: code-intelligence-substrate
workstream: WS-01
pr: 1201
merge_commit: `28cce1bf0`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/120-documentation-surface-provider/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — all 5 deliverables shipped; 2 fully confirmed, 3 partial. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

The `documentation` module is now real and doc-corpus de-duplication works. But the shipped reference-resolution engine **over-reports dangling references** (10 of 18 flagged are valid), and the shared suppression-note renderer under-counts its population by 18x and 504x — a substrate defect this plan exposed rather than caused.

## Premise verdict

**Refuted, then rebuilt.** Re-derivation found the founding premise false in the clone: the doc corpus was NOT double-indexed, and no `documentation` module existed at all, because `discover_modules` used a non-recursive glob that missed every nested doc. The operator chose to build the intended end state (make the module real) rather than re-scope on the refutation.

## Gaps carried out of this landing

**14 total — 2 high, 5 medium, 7 low.** High: G1, G3.

- **Creating the `documentation` module was a genuine module-set change** (12 -> 13 modules here) whose full consumer population — phase-4 planning, task-profile resolution, module-tests scoping — was **never derived**. Only the "docs-only change derives zero builds" consequence was checked.
- G3 (the suppression miscount) belongs to the **shared `component_refs` schema and renderer**, not to the doc engine — every Axis-C resolver on the roster shares it.
- The `find` / `which-module` owner-naming divergence for singly-inventoried claimed files is real and will recur for any future Axis-D claim (G14).

## Inconsistencies found, and what was verified

- Report's "zero false positives across 803 real references" | verified by re-executing `build_doc_component_refs` at HEAD | **verdict: the claim was plausibly true on its measurement date** (the file carrying all 10 false positives arrived in a later PR), **but it is stated as a general property of the engine and does not hold** — G1 is real and unfixed.

## Residue

D4's GitHub-slug hyphen-collapse false-positive class left unfixed at landing; D2's wiring has zero integration coverage (mutation survives); `client-api.md` never received the precedence rule D2 requires.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-024 --status shipped`
- [x] row `pr` stamped `1201` — `orchestrator queue --set-row PLAN-CIS-024 --field pr --value 1201`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-024 --field landing --value landings/PLAN-CIS-024.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G1 routes to **PLAN-CIS-049** (`510`); G3 is a shared-substrate item and routes there too. The underived consumer population of the new module is recorded as a Watch.
