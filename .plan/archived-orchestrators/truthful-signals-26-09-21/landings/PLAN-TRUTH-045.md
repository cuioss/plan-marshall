# Landing Analysis: PLAN-TRUTH-045 — the dispatch audit has an empty primary surface and a retry blind secondary one

epic: truthful-signals
workstream: WS-01
pr: #1200 — merged as `1da26b137`
cloud-run: `cloud-runs/280-the-dispatch-audit-has-an-empty-primary-surface-and-a-retry-blind-secondary-one/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/280-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G6 — planning lane / dispatch / manifest / test suite.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | 4/4 (rollout 6 of 22 sites) |
| Gaps filed | 7 (high 2 · medium 3 · low 2) |
| Closed at HEAD | **0** — none |
| **Still open** | **7** |

## Carry-forward

The seam is correct and per-firing, but only 6 of 22 dispatch sites use it — and the same commit that left 11 hand-written `[DISPATCH]` blocks rewrote the standard to call that shape forbidden, with `planning.md:275` still instructing it AND citing the forbidding section as its authority.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/280-the-dispatch-audit-has-an-empty-primary-surface-and-a-retry-blind-secondary-one/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 0 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1200`
- [x] row `landing` = `landings/PLAN-TRUTH-045.md`
- [x] cloud-run artifacts ingested to `cloud-runs/280-the-dispatch-audit-has-an-empty-primary-surface-and-a-retry-blind-secondary-one/`
- [x] gap closure re-derived at HEAD (0 of 7 closed)
