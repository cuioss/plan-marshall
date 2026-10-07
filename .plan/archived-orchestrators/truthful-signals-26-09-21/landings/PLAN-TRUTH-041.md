# Landing Analysis: PLAN-TRUTH-041 — java skills route authors to an anti pattern they never warn about

epic: truthful-signals
workstream: WS-01
pr: #1195 — merged as `a75060de9`
cloud-run: `cloud-runs/270-java-skills-route-authors-to-an-anti-pattern-they-never-warn-about/`

> Ingested from the standalone cloud lane (`doc/plans/truthful-signals/270-…`) on 2026-08-22.
> The landing was corroborated FIRST-PARTY by locating the merge commit in `main` — not from PR
> state and not from the run report's own header, two of which were found stale. Verified and
> adversarially reviewed by the epic audit (PR #1298), then re-grounded at HEAD during ingestion.
> Group analysis: [`cloud-runs/_epic/ingestion-analysis.md`](../cloud-runs/_epic/ingestion-analysis.md) § Group G1 — plugin-doctor / documentation surfaces.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | 6/6 |
| Gaps filed | 7 (high 1 · medium 3 · low 3) |
| Closed at HEAD | **0** — none |
| **Still open** | **7** |

## Carry-forward

The rule landed only in `java-null-safety`, an OPTIONAL skill, while `java-core` — a DEFAULT skill advertising "null-safety" — teaches records and carries no pointer. The original failure path is still the default-configuration path. ⛔ No remediation pass.

## Artifacts

`plan.md`, `report-01.md`, `verification.md`, `gaps.md` — all four retained verbatim under
`cloud-runs/270-java-skills-route-authors-to-an-anti-pattern-they-never-warn-about/`. The `gaps.md` open count is a SNAPSHOT at PR #1298 and overstates the live
set by the 0 closed above; re-ground before scheduling any of it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1195`
- [x] row `landing` = `landings/PLAN-TRUTH-041.md`
- [x] cloud-run artifacts ingested to `cloud-runs/270-java-skills-route-authors-to-an-anti-pattern-they-never-warn-about/`
- [x] gap closure re-derived at HEAD (0 of 7 closed)
