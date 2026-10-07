# Landing Analysis: PLAN-TRUTH-007 — key order canonicalization unreachable and false green

epic: truthful-signals
workstream: WS-01
pr: #1156 — merged as `10de4d127`
cloud-run: `cloud-runs/080-key-order-canonicalization-unreachable-and-false-green/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/080-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G7 — git / artifacts / cloud lane / generator.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | 10/10 (D3 = re-derived refutation) |
| Gaps filed | 9 (high 1 · medium 6 · low 2) |
| Closed at HEAD | **0** — none |
| **Still open** | **9** |

## Carry-forward

⛔ G9 open: `ClaudeRuntime.project_initial_setup` unconditionally overwrites `marshal.json` with no read and no existence check — the maximal lost update on the very file D4 was written to protect.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/080-key-order-canonicalization-unreachable-and-false-green/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 0 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1156`
- [x] row `landing` = `landings/PLAN-TRUTH-007.md`
- [x] cloud-run artifacts ingested to `cloud-runs/080-key-order-canonicalization-unreachable-and-false-green/`
- [x] gap closure re-derived at HEAD (0 of 9 closed)
