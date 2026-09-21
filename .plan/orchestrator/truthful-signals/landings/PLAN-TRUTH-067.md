# Landing Analysis: PLAN-TRUTH-067 — derive verification emits a build class phase 5 cannot route

epic: truthful-signals
workstream: WS-01
pr: #1222 — merged as `ebd001860`
cloud-run: `cloud-runs/340-derive-verification-emits-a-build-class-phase-5-cannot-route/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/340-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G6 — planning lane / dispatch / manifest / test suite.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | 5/5 — D1/D2 reversed |
| Gaps filed | 4 (high 0 · medium 3 · low 1) |
| Closed at HEAD | **0** — none |
| **Still open** | **4** |

## Carry-forward

D1/D2 were reversed by operator decision at the D0 gate; the emitter was never touched. ⛔ The only authorisation is the report's own assertion of an AskUserQuestion exchange, with NO TREE ARTIFACT — a reviewer declining that word reads the plan as partially-implemented.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/340-derive-verification-emits-a-build-class-phase-5-cannot-route/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 0 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1222`
- [x] row `landing` = `landings/PLAN-TRUTH-067.md`
- [x] cloud-run artifacts ingested to `cloud-runs/340-derive-verification-emits-a-build-class-phase-5-cannot-route/`
- [x] gap closure re-derived at HEAD (0 of 4 closed)
