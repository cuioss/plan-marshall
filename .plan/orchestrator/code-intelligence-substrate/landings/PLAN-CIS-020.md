# Landing Analysis: PLAN-CIS-020 — Retrospective report sections structurally dead

epic: code-intelligence-substrate
workstream: WS-04
pr: 1287
merge_commit: `9135f27`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/330-retrospective-report-sections-structurally-dead/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 5 of 5 deliverables shipped. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

All five deliverables landed and the written-implies-non-empty invariant now holds correctly for dict fragments, after four internal verification rounds. **But a non-dict fragment — a string, int or list — on a conditional row is still silently classified as a benign "omission"** (the identical partition defect, one type class over), and three conditional rows fire a false content-loss `warning` on every ordinary clean-run plan.

## Premise verdict

Confirmed that the three-way written/omitted/dropped partition, once fixed, discriminates correctly for dict-shaped fragments (round 4's 34-input-class differential found nothing over two trees). **Refuted at a type boundary the run never tested**: `_fragment_renders_empty` and `_fragment_has_payload` disagree on any non-dict value — string, int and list all read as *content* on one path and *no payload* on the other, reachable in production via an aspect that writes prose.

## Gaps carried out of this landing

**16 total — 3 high, 6 medium, 7 low.** High: G1, G2, G6.

- **G2 (high) is the loudest live defect in this ingest**: a false `warning` fires on the common, clean-run path *today*. A signal that fires on every run stops being read.
- **G6 (high): the report's headline "Executive Summary" section has literally never been produced by any run** — the compiler's `written` branch for it is unreachable in production.
- **G9 is the surviving vacuity**: the table-to-registry correspondence guard checks only one direction, so a new dead registry row ships undetected — exactly the shape of the two dead rows this plan itself found and deliberately left unfixed.

## Inconsistencies found, and what was verified

- Report's Step-9 contract-check row names a merge-gate head one commit before the PR's actual merged head | verified by comparing the PR head against the report row | **verdict: confirmed, and structurally near-unavoidable** — a report cannot name its own SHA. Recorded as a minor report defect.

## Residue

D2's two dead registry rows are deliberately unremediated (the deliverable is *mutates nothing*). The highest-value follow-up the run itself names — the three false-`warning` conditional rows — is explicitly deferred because no deliverable in the plan authorised a drop-side change.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-020 --status shipped`
- [x] row `pr` stamped `1287` — `orchestrator queue --set-row PLAN-CIS-020 --field pr --value 1287`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-020 --field landing --value landings/PLAN-CIS-020.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

**G2 is the one item in batch D worth pulling forward on its own** — it degrades every clean run today. Routes to **PLAN-CIS-051** (`530`), as do G1 and G6; G9 routes to **PLAN-CIS-053** (`550`).
