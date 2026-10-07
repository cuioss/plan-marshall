# History: truthful-signals-26-09-21

slug: truthful-signals-26-09-21

## Outcome

Archived on 2026-09-21 as part of a broader orchestrator restructuring: the live
`truthful-signals` epic had accumulated 225 plan rows, 196 of them terminal (shipped,
superseded, transferred, retired). This epic exists to carry that terminal history off
the live queue so `truthful-signals` can restart with a clean, small live surface.

At the same time, the sibling epic `quality-aspect` (the same "confident signal hides a
caveat" defect archetype, scoped specifically to the finalize lane) was fully merged
into `truthful-signals`. Its 3 shipped rows (originally PLAN-01 ledger-joins, PLAN-07
footprint-surface, PLAN-09 outline-sweep) were renumbered PLAN-204/210/212 to avoid id
collision with truthful-signals' own PLAN-01..19 range, and archived here alongside
truthful-signals' own terminal rows. quality-aspect's 15 live/staged rows were likewise
renumbered (PLAN-205 through PLAN-221, excluding the three above) and joined the live
`truthful-signals` queue as workstreams `WS-QA-01` through `WS-QA-09`.

## Final queue (199 rows, all terminal)

- 196 rows carried over unchanged from `truthful-signals` (shipped: bulk of the set;
  superseded: the large PLAN-TRUTH-09x through -15x cluster, mostly folded into later
  consolidated specs per their `superseded_by` pointers; transferred: PLAN-116, -60,
  -100, -117, -119, PLAN-TRUTH-152; retired: PLAN-TRUTH-092).
- 3 rows merged in from `quality-aspect`, renumbered:
  - PLAN-204 (was PLAN-01, `ledger-joins`) — shipped, PR #1545
  - PLAN-210 (was PLAN-07, `footprint-surface`) — shipped, PR #1559
  - PLAN-212 (was PLAN-09, `outline-sweep`) — shipped, PR #1551

## Decision record

- 2026-09-21 — Split + merge executed per operator direction (orchestrator restructuring
  pass). quality-aspect fully absorbed into truthful-signals rather than kept as an
  independent sibling, because the two shared one defect archetype and the split was
  purely lane-scope, not subject-matter.

## Carried-forward leads

None specific to this archive — any unresolved thread belonging to a terminal row lives
in that row's own `landings/PLAN-NN.md` document, which travelled with it into this
archive. The live continuation of both epics' unfinished work is in `truthful-signals`'
own `epic.md` / `status.json`.

## Unresolved defects and watches carried into truthful-signals (live)

None specific to the split itself. Pre-existing open defects and watches belonging to
truthful-signals' still-live rows remain recorded in the live epic, not here.
