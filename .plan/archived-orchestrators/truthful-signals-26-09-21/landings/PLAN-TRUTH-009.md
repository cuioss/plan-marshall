# Landing Analysis: PLAN-TRUTH-009 — surface every knob in marshal json

epic: truthful-signals
workstream: WS-01
pr: #1155 — merged as `8f23d7d27`
cloud-run: `cloud-runs/090-surface-every-knob-in-marshal-json/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/090-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G4 — config / steward / version selection / daemon.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | 5/5 |
| Gaps filed | 3 (high 1 · medium 1 · low 1) |
| Closed at HEAD | **3** — G1, G2, G3 |
| **Still open** | **0** |

## Carry-forward

The run skipped the one surface its own Rule 4 calls "the most-forgotten" — the TRACKED `.plan/marshal.json` — on a premise false on both halves; a plan about discoverability left its own dogfooding config hiding both knobs. All 3 gaps since closed.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/090-surface-every-knob-in-marshal-json/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 3 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1155`
- [x] row `landing` = `landings/PLAN-TRUTH-009.md`
- [x] cloud-run artifacts ingested to `cloud-runs/090-surface-every-knob-in-marshal-json/`
- [x] gap closure re-derived at HEAD (3 of 3 closed)
