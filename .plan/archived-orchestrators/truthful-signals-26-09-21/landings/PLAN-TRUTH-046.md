# Landing Analysis: PLAN-TRUTH-046 — main sha records the worktree head and config hash cannot fail usefully

epic: truthful-signals
workstream: WS-01
pr: #1205 — merged as `b2982e75d`
cloud-run: `cloud-runs/290-main-sha-records-the-worktree-head-and-config-hash-cannot-fail-usefully/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/290-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G5 — metrics / ledger readers / timestamps.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | 3/3 |
| Gaps filed | 5 (high 1 · medium 2 · low 2) |
| Closed at HEAD | **0** — none |
| **Still open** | **5** |

## Carry-forward

⛔ The shipped fix is correct but THE DIAGNOSIS IS FALSE and now lives in a production docstring — the executor strips `--audit-plan-id`, so the "signal never fired" story would send a reader to "fix" 28 documented, working call sites.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/290-main-sha-records-the-worktree-head-and-config-hash-cannot-fail-usefully/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 0 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1205`
- [x] row `landing` = `landings/PLAN-TRUTH-046.md`
- [x] cloud-run artifacts ingested to `cloud-runs/290-main-sha-records-the-worktree-head-and-config-hash-cannot-fail-usefully/`
- [x] gap closure re-derived at HEAD (0 of 5 closed)
