# Landing Analysis: PLAN-TRUTH-069 — collapse the version selection machinery

epic: truthful-signals
workstream: WS-01
pr: #1223 — merged as `d01edfdfd`
cloud-run: `cloud-runs/360-collapse-the-version-selection-machinery/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/360-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G4 — config / steward / version selection / daemon.

## Verdict

| Field | Value |
|---|---|
| Verdict | **partially-implemented** |
| Deliverables | 6/7 — D1 did not land |
| Gaps filed | 6 (high 1 · medium 3 · low 2) |
| Closed at HEAD | **1** — G3 |
| **Still open** | **5** |

## Carry-forward

⛔ THE ROOT LEVER NEVER SHIPPED. Absolute version-pinned paths are still baked into the executor; what landed is marker-removal from a resolver that was ALREADY runtime. D1's own Done-when passes, and passed pre-fix too.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/360-collapse-the-version-selection-machinery/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 1 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1223`
- [x] row `landing` = `landings/PLAN-TRUTH-069.md`
- [x] cloud-run artifacts ingested to `cloud-runs/360-collapse-the-version-selection-machinery/`
- [x] gap closure re-derived at HEAD (1 of 6 closed)
