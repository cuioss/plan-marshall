# Landing Analysis: PLAN-TRUTH-018 — configurable display timezone for rendered timestamps

epic: truthful-signals
workstream: WS-01
pr: #1172 — merged as `72338ad33`
cloud-run: `cloud-runs/150-configurable-display-timezone-for-rendered-timestamps/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/150-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G5 — metrics / ledger readers / timestamps.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | 5/5 |
| Gaps filed | 5 (high 2 · medium 2 · low 1) |
| Closed at HEAD | **0** — none |
| **Still open** | **5** |

## Carry-forward

The knob reaches 2 RENDER sites and its write-path guard is FILE-granular, so converting any of the 9 persisted `now_utc_iso()` writes in `manage-metrics.py` passes the guard green; D5(c) cannot observe that defect class at all.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/150-configurable-display-timezone-for-rendered-timestamps/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 0 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1172`
- [x] row `landing` = `landings/PLAN-TRUTH-018.md`
- [x] cloud-run artifacts ingested to `cloud-runs/150-configurable-display-timezone-for-rendered-timestamps/`
- [x] gap closure re-derived at HEAD (0 of 5 closed)
