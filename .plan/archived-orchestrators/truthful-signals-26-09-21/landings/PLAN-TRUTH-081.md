# Landing Analysis: PLAN-TRUTH-081 — cloud lane assumes local runtime affordances

epic: truthful-signals
workstream: WS-01
pr: #1147 — merged as `a3eb36bb8`
cloud-run: `cloud-runs/450-cloud-lane-assumes-local-runtime-affordances/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/450-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G7 — git / artifacts / cloud lane / generator.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | 6/6 |
| Gaps filed | 5 (high 1 · medium 3 · low 1) |
| Closed at HEAD | **0** — none |
| **Still open** | **5** |

## Carry-forward

⛔ The plan that exists to make the cloud lane state its affordances truthfully shipped a report that DENIES HAVING DONE THE VERY THINGS IT DID (five cells say "no PR opened"; PR #1147 merged as a3eb36bb8). The epic's archetype committed inside the fix for it.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/450-cloud-lane-assumes-local-runtime-affordances/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 0 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1147`
- [x] row `landing` = `landings/PLAN-TRUTH-081.md`
- [x] cloud-run artifacts ingested to `cloud-runs/450-cloud-lane-assumes-local-runtime-affordances/`
- [x] gap closure re-derived at HEAD (0 of 5 closed)
