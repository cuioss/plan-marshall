# Landing Analysis: PLAN-TRUTH-063 — merge gate cannot tell a required check from a decorative one

epic: truthful-signals
workstream: WS-01
pr: #1137 — merged as `991f3e5fb`
cloud-run: `cloud-runs/030-merge-gate-cannot-tell-a-required-check-from-a-decorative-one/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/030-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G2 — finalize / CI / merge gates.

## Verdict

| Field | Value |
|---|---|
| Verdict | **partially-implemented** |
| Deliverables | 4/6 — D0 partial, D3 dropped |
| Gaps filed | 4 (high 0 · medium 2 · low 2) |
| Closed at HEAD | **0** — none |
| **Still open** | **4** |

## Carry-forward

Required-ness on the cloud path is readable only from `mergeStateStatus` (the ruleset-config API returns 403), so any instruction to "derive the required set" is unexecutable there.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/030-merge-gate-cannot-tell-a-required-check-from-a-decorative-one/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 0 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1137`
- [x] row `landing` = `landings/PLAN-TRUTH-063.md`
- [x] cloud-run artifacts ingested to `cloud-runs/030-merge-gate-cannot-tell-a-required-check-from-a-decorative-one/`
- [x] gap closure re-derived at HEAD (0 of 4 closed)
