# Landing Analysis: PLAN-TRUTH-012 — canonical block diverges from argparse choices

epic: truthful-signals
workstream: WS-01
pr: #1158 — merged as `b59f3b93e`
cloud-run: `cloud-runs/100-canonical-block-diverges-from-argparse-choices/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/100-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G1 — plugin-doctor / documentation surfaces.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | 6/6 |
| Gaps filed | 10 (high 2 · medium 8 · low 0) |
| Closed at HEAD | **3** — G6, G7, G10 |
| **Still open** | **7** |

## Carry-forward

⛔ Both named leads were recorded REFUTED on evidence about the canonical block while the claim-label named the whole SKILL.md — the leads are live at the sites actually named. A false refutation inside a plan about false oracles.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/100-canonical-block-diverges-from-argparse-choices/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 3 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1158`
- [x] row `landing` = `landings/PLAN-TRUTH-012.md`
- [x] cloud-run artifacts ingested to `cloud-runs/100-canonical-block-diverges-from-argparse-choices/`
- [x] gap closure re-derived at HEAD (3 of 10 closed)
