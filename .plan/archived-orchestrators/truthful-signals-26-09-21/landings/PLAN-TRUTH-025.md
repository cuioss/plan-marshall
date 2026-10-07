# Landing Analysis: PLAN-TRUTH-025 — named recovery discards operator config

epic: truthful-signals
workstream: WS-01
pr: #1186 — merged as `b87e0751c`
cloud-run: `cloud-runs/210-named-recovery-discards-operator-config/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/210-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G4 — config / steward / version selection / daemon.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | 4/4 |
| Gaps filed | 5 (high 3 · medium 1 · low 1) |
| Closed at HEAD | **0** — none |
| **Still open** | **5** |

## Carry-forward

The D2 collapse is real but its guard is VACUOUS — `_references_authority(text)` is two substring checks both true by construction for any region carrying the standard cross-reference bullet; a reworded destructive block passes 3 of 3 tests green.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/210-named-recovery-discards-operator-config/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 0 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1186`
- [x] row `landing` = `landings/PLAN-TRUTH-025.md`
- [x] cloud-run artifacts ingested to `cloud-runs/210-named-recovery-discards-operator-config/`
- [x] gap closure re-derived at HEAD (0 of 5 closed)
