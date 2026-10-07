# History: quality-aspect

slug: quality-aspect

## Outcome

Closed 2026-09-21: fully merged into `truthful-signals`, which owns the same
"confident signal hides a caveat" defect archetype — quality-aspect was that archetype
scoped specifically to the finalize lane, spun off from the now-archived
`finalize-machinery`. On reconsideration during an orchestrator restructuring pass, the
lane-scoping did not justify a separate epic: the two shared one identity.

## Disposition of the 18-row queue

All rows renumbered to avoid id collision with truthful-signals' own PLAN-01..19 range
(old → new):

| Old id | New id | Slug | Disposition |
|--------|--------|------|-------------|
| PLAN-01 | PLAN-204 | ledger-joins | shipped — archived to `truthful-signals-26-09-21` |
| PLAN-02 | PLAN-205 | build-telemetry | staged — joined `truthful-signals` live queue (WS-QA-01) |
| PLAN-03 | PLAN-206 | verify-first-a | staged — joined `truthful-signals` (WS-QA-02) |
| PLAN-04 | PLAN-207 | verify-first-b | staged — joined `truthful-signals` (WS-QA-02) |
| PLAN-05 | PLAN-208 | review-yield-a | staged — joined `truthful-signals` (WS-QA-03) |
| PLAN-06 | PLAN-209 | review-yield-b | staged — joined `truthful-signals` (WS-QA-03) |
| PLAN-07 | PLAN-210 | footprint-surface | shipped — archived to `truthful-signals-26-09-21` |
| PLAN-08 | PLAN-211 | baseline-reconcile | staged — joined `truthful-signals` (WS-QA-04) |
| PLAN-09 | PLAN-212 | outline-sweep | shipped — archived to `truthful-signals-26-09-21` |
| PLAN-10 | PLAN-213 | plan-execute-mechanics | staged — joined `truthful-signals` (WS-QA-06) |
| PLAN-11 | PLAN-214 | gates-anchors | staged — joined `truthful-signals` (WS-QA-06) |
| PLAN-12 | PLAN-215 | worktree-paths | staged — joined `truthful-signals` (WS-QA-06) |
| PLAN-13 | PLAN-216 | self-review-detectors | staged — joined `truthful-signals` (WS-QA-07) |
| PLAN-14 | PLAN-217 | chat-signal-halt | staged — joined `truthful-signals` (WS-QA-07) |
| PLAN-15 | PLAN-218 | testing-fidelity | staged — joined `truthful-signals` (WS-QA-09) |
| PLAN-17 | PLAN-219 | finalize-self-review | staged — joined `truthful-signals` (WS-QA-08) |
| PLAN-18 | PLAN-220 | cost-mergequeue | staged — joined `truthful-signals` (WS-QA-08) |
| PLAN-19 | PLAN-221 | executor-target-fidelity | staged — joined `truthful-signals` (WS-QA-02) |

3 shipped rows travel to the `truthful-signals-26-09-21` archive (alongside
truthful-signals' own 196 terminal rows); 15 staged rows travel to the live
`truthful-signals` queue as workstreams `WS-QA-01` through `WS-QA-09`.

## Decision record

- 2026-09-21 — Merge into truthful-signals rather than keep as an independent sibling.
  Reasoning: same defect archetype, lane-scope alone did not warrant a separate ledger.

## Carried-forward leads

None beyond what travelled with each row's own spec/landing file.
