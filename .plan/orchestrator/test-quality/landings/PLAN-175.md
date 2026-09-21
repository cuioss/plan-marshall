# Landing Analysis: PLAN-175 — Harden the shipped shape scanners

epic: test-quality
workstream: WS-03
pr: #1506

> Landing record for one shipped plan. Lives at `landings/PLAN-175.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Spec: `plans/PLAN-175-harden-the-shipped-shape-scanners.md` (4 deliverables). Merge
`4d68ad6db` ("test(shape-scan): harden scanners with falsifiable controls (#1506)")
touches exactly one file: `test/test_harness_shape_guards.py` (+59/−8).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — matched negative controls over equivalent spellings | shipped-as-specified (verified satisfied, no code change) | Merge diff touches no detector file; `_test_shape_scan.py` unmodified at merge — consistent with controls passing against already-construct-based detectors |
| D2 — re-express non-entailing guards | shipped-as-specified (verified satisfied) + one shipped fix | `d3255c1`: R1/R4/R5 armed guards now assert `result.clean` instead of `not result.hits` — guards fail closed on unmeasured coverage |
| D3 — normalize both sides of path comparisons | shipped-as-specified | `9e4d53017`: absolute-path exemption pair, reachable under relative and absolute caller paths |
| D4 — report scanned vs unclassifiable population | shipped-as-specified | `9e4d53017`: reproducing-command diagnostics in guard output |

Guard suite 25/25 pass (operator-reported; merge eligibility corroborates a green gate).

## Metrics and Anomalies

- Tokens: `total_tokens=0` in landing-facts — NOT a real zero. `record-metrics` ran with
  enrich skipped per session override (logged), so phase totals are a floor without
  transcript tokens. Do not cite a token figure for this plan; the finalize-cost
  comparison must exclude it.
- Duration: `total_wall_seconds=25317` (~7h02m) from landing-facts.
- Anomalies: none. Quota waits 2/10 × 90 min (CodeRabbit rate windows, reset on
  schedule both times); no PR close/recreate. Blocked once at finalize entry on the
  session-capture block (`hook_not_configured`) — aborted per contract, resumed via
  `/marshall-steward` + finalize from worktree. No harness kills reported.

## Routing and Merge Behavior

- Review (operator-reported, merge outcome corroborates): mandatory CodeRabbit done —
  review 1 (at `9e4d5`) 1 actionable finding → addressed in `d3255c1`, thread resolved;
  review 2 (at `d3255c1`) 0 actionable, merge risk minimal. Sourcery approved ×2.
  `cuioss-review-bot` no issues. CI 10/10 green.
- CI/merge: queue-merged as `4d68ad6db`; no rebase conflicts, no re-verify signals, no
  observed collision (nothing else was in flight). Branch deleted ✓, worktree
  deregistered from `git worktree list` ✓. Residual: the worktree directory still
  exists on disk with build artifacts (`.venv`, `.mypy_cache`) — deregistered but not
  removed; harmless, noted here rather than as a defect (`cleanup_owed=false`).
- Declared-vs-realized data point for the live declaration-form question: declared 4
  entries, realized 1 file. The two untouched test files were control-target files,
  never modification claims — OVER-declaration with no false collision this time
  (nothing else running), the benign direction, same class as PLAN-165/plan-06 but
  without the emit cost.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-175 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-175 --field pr --value #1506`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-175 --field landing --value landings/PLAN-175.md`
- [x] row `plan_marshall_plan_id` stamped (at launch) — value `harden-the-shipped-shape-scanners`
- [x] epic.md queue reconciled from status.json
- [x] no new defect/watch; orphan worktree dir noted above as residual, not a defect
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator compact --slug test-quality`

## Follow-Ups

- None staged. Remaining open work is PLAN-140 (staged, sequenced — DERIVED surface).
  The D1/D2 no-change outcome sharpens a future PLAN-140 sequencing fact: the
  instrument PLAN-175 hardened is load-bearing for the campaign runs, and it held
  without modification.
