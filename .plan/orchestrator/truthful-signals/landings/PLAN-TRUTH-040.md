# Landing Analysis: PLAN-TRUTH-040 — the generic dispatch template cannot carry a step specific mandatory field

epic: truthful-signals
workstream: WS-01
pr: #1197 — merged as `95116c073`
cloud-run: `cloud-runs/260-the-generic-dispatch-template-cannot-carry-a-step-specific-mandatory-field/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/260-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G6 — planning lane / dispatch / manifest / test suite.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | 4/4 |
| Gaps filed | 7 (high 2 · medium 1 · low 4) |
| Closed at HEAD | **0** — none |
| **Still open** | **7** |

## Carry-forward

D2 added a THIRD declaration surface and linked two of three; the input-table `Required: Yes` row that the ext-point doc itself names as the declaration surface is read by nothing, so the original defect still reproduces for 24 of 26 steps.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/260-the-generic-dispatch-template-cannot-carry-a-step-specific-mandatory-field/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 0 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1197`
- [x] row `landing` = `landings/PLAN-TRUTH-040.md`
- [x] cloud-run artifacts ingested to `cloud-runs/260-the-generic-dispatch-template-cannot-carry-a-step-specific-mandatory-field/`
- [x] gap closure re-derived at HEAD (0 of 7 closed)
