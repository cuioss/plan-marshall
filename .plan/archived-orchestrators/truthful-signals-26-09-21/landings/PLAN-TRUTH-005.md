# Landing Analysis: PLAN-TRUTH-005 — marshalld self reload on version signal

epic: truthful-signals
workstream: WS-01
pr: #1152 — merged as `8f3c7fe0e`
cloud-run: `cloud-runs/070-marshalld-self-reload-on-version-signal/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/070-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G4 — config / steward / version selection / daemon.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | 6/6 |
| Gaps filed | 6 (high 1 · medium 4 · low 1) |
| Closed at HEAD | **0** — none |
| **Still open** | **6** |

## Carry-forward

⛔ The contract's safety premise is FALSE for exactly the population the reconcile targets: a daemon pinned below the counts extension answers the handshake without them, `run_status` writes 0, and reconcile DRAINS A LIVE BUILD.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/070-marshalld-self-reload-on-version-signal/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 0 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1152`
- [x] row `landing` = `landings/PLAN-TRUTH-005.md`
- [x] cloud-run artifacts ingested to `cloud-runs/070-marshalld-self-reload-on-version-signal/`
- [x] gap closure re-derived at HEAD (0 of 6 closed)
