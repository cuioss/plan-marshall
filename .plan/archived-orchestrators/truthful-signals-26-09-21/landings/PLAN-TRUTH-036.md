# Landing Analysis: PLAN-TRUTH-036 — deep lane bought by one signal while the discriminating field is null

epic: truthful-signals
workstream: WS-01
pr: #1188 — merged as `01e8c8f80`
cloud-run: `cloud-runs/240-deep-lane-bought-by-one-signal-while-the-discriminating-field-is-null/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/240-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G6 — planning lane / dispatch / manifest / test suite.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | 4/4 |
| Gaps filed | 5 (high 1 · medium 2 · low 2) |
| Closed at HEAD | **0** — none |
| **Still open** | **5** |

## Carry-forward

S7 is suppressed whenever the scope band is `single_module` — but that band is also what `classify_scope_pure` assigns when it found NO PATH AT ALL, so a false positive was closed by shipping a false negative into the same seam.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/240-deep-lane-bought-by-one-signal-while-the-discriminating-field-is-null/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 0 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1188`
- [x] row `landing` = `landings/PLAN-TRUTH-036.md`
- [x] cloud-run artifacts ingested to `cloud-runs/240-deep-lane-bought-by-one-signal-while-the-discriminating-field-is-null/`
- [x] gap closure re-derived at HEAD (0 of 5 closed)
