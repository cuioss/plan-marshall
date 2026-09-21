# Landing Analysis: PLAN-TRUTH-082 — audit ledger reader reads undatable zero as measured

epic: truthful-signals
workstream: WS-01
pr: #1278 — merged as `d1c31533b`
cloud-run: `cloud-runs/460-audit-ledger-reader-reads-undatable-zero-as-measured/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/460-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G5 — metrics / ledger readers / timestamps.

## Verdict

| Field | Value |
|---|---|
| Verdict | **fully-implemented** |
| Deliverables | 4/4 clean |
| Gaps filed | 5 (high 0 · medium 3 · low 2) |
| Closed at HEAD | **1** — G5 |
| **Still open** | **4** |

## Carry-forward

⛔ The gate is semantically correct but ARITHMETICALLY INERT — all four consumers route the value through `.get(field,0)`, `>0`, `>row_value` or `max(...)`, in each of which absent and measured-0 are indistinguishable. It corrects the readers' contract, not any emitted number.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/460-audit-ledger-reader-reads-undatable-zero-as-measured/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 1 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1278`
- [x] row `landing` = `landings/PLAN-TRUTH-082.md`
- [x] cloud-run artifacts ingested to `cloud-runs/460-audit-ledger-reader-reads-undatable-zero-as-measured/`
- [x] gap closure re-derived at HEAD (1 of 5 closed)
