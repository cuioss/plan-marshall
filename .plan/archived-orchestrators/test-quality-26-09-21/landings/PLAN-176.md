# Landing Analysis: PLAN-176 — Module-Budget Campaign, Run 2 (Slice 040)

epic: test-quality
workstream: WS-04
pr: #1514, #1515, #1526, #1517, #1518, #1519, #1520, #1521, #1522

> Landing record for one shipped plan. Written by the `analyze` verb (inbox-scan
> drain) after verifying claims against ground truth. Note: the inbox landing
> message carried `complete: false` (`merge_state`/`cleanup_owed` unknown) — the
> missing facts were corroborated independently below and recorded as an Open
> Defect per the drain contract, not reconciled-as-if-complete.

## Deliverable Fidelity vs Spec

Spec: `plans/PLAN-176-module-budget-campaign-run-2-slice-040.md` (D1–D5, one
self-contained run). Landed as **9 behaviour-cluster carve PRs** (the plan PR
#1513 closed unmerged at 225 files vs the 100-file review cap; #1516 superseded):

| Carve (merge) | PR | Scope |
|---------------|----|-------|
| `b5978998f` | #1514 | automatic-review (1/9) |
| `5f8206687` | #1515 | manage-ci-artifacts (2/9) |
| `3832d7dd2` | #1526 | phase-6-finalize (3/9) |
| `c1248fa35` | #1517 | tools-integration-ci (4/9) |
| `10dcfddbb` | #1518 | workflow-integration-git (5/9) |
| `5eccf94c3` | #1519 | workflow-integration-github (6/9) |
| `499c90d80` | #1520 | workflow-integration-gitlab (7/9) |
| `6208f5497` | #1521 | workflow-integration-sonar (8/9) |
| `756555079` | #1522 | workflow-pr-doctor (9/9) |

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — re-derive before acting | shipped-as-specified | 9 over-budget `test/plan-marshall/` modules identified and split; slice counts verified on main (automatic-review 32 files corroborated by glob; workflow-integration-github 64 files in #1519 stat) |
| D2 — split by behaviour cluster, never a class | shipped-as-specified | #1519 stat: 64 files, cluster-per-source shape (`test_github.py` 682 − → cluster files); splitter discipline from lesson `2026-09-17-15-001` folded pre-launch |
| D3 — prove nothing was lost | shipped-as-specified | Per-carve fidelity multisets (operator-reported, CI-green per carve); byte-for-byte character visible in diffs (pure −/+ moves, e.g. `test_github_pr.py` 4408 − redistributed) |
| D4 — order-independence | shipped-as-specified | Default + reverse passing per run (operator-reported) |
| D5 — report the measured deltas | shipped-as-specified with noted incidents | R5 severance, skip-gate retarget, #1509 drift port, conftest reconstruction — all closed in-run, see below |

⚠️ Count vocabulary: landing-facts reports `deliverables_total/done = 9/9` (carve-sized
units); the spec counts D1–D5. Both true; the 9 is carves, the 5 is the method. No
discrepancy beyond units.

## Metrics and Anomalies

- Tokens: `total_tokens=0` — NOT a real zero. `record-metrics` ran with enrich skipped
  per operator session override (logged), so phase totals are a floor without
  transcript tokens. **Exclude this run from finalize-cost comparisons**, as with
  PLAN-175.
- Duration: `total_wall_seconds=99273` (~27h34m) from landing-facts.
- Incidents (all closed in-run, operator-reported with corroborating merges):
  - **R5 guard severance (15 hits):** splits separated parametrized sites from their
    file-scoped cardinality pins → 3 fix tasks, loop-back 1, 0 hits after.
  - **Skip-gate stale nodeid:** a split renamed a file keyed in `_SKIP_EXCEPTIONS` →
    1-line retarget.
  - **Upstream #1509 drift:** tolerated-delete change landed mid-run; 2 prune-ref
    tests ported onto the affected carve.
  - **Carve-conftest reconstruction:** shared `conftest.py` roster rebuilt per carve
    with machine-checked set-equality proofs (script in `.plan/temp/`).
  - **CodeRabbit quota:** 5 × 90-min waits per the operator ladder; close/recreate
    avoided; reviews completed for all merged PRs.
  - **Plan-side corrections:** two ledger rows carried documented corrections (D9 path
    typo, one hand-expanded SHA), both superseded by corrected appends with
    decision-log notes — self-healed, no orchestrator action.

## Routing and Merge Behavior

- Review (operator-reported, corroborated by merges + lesson 002): 3 actionable
  bot findings fixed in-run; 18 acknowledged without change, 0 rejected
  (no mis-triage). Reviews completed for all 9 merged PRs.
- CI/merge: 9/9 queue-merged green, one carve at a time (N=1 sequential — no
  intra-epic collision possible). #1513 closed unmerged (oversized, 225 files);
  #1516 superseded (operator-reported, by a successor carve).
- Branch deleted ✓, worktree deregistered ✓, plan archived at
  `.plan/local/archived-plans/2026-09-18-module-budget-campaign-run-2-slice-040/` ✓.
- No collision observed. Realized footprint (`test/plan-marshall/*` splits) vs
  PLAN-177's declared surface (`marketplace/...plugin-doctor`,
  `test/pm-plugin-development/plugin-doctor/`, `test_staleness_guard.py`): disjoint
  to the file.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-176 --status shipped` (direct from `staged`: launch/running were never recorded — the operator ran without a start report, as with PLAN-155's skipped-`running`; evidence for both is the 9 merges + archived plan)
- [x] row `pr` stamped — 9 carve numbers (plan PR #1513 closed, not stamped)
- [x] row `landing` stamped — `landings/PLAN-176.md`
- [x] row `plan_marshall_plan_id` stamped — `module-budget-campaign-run-2-slice-040`
- [x] epic.md queue reconciled from status.json
- [x] Open Defect: incomplete landing-facts (`merge_state`/`cleanup_owed` unknown) — facts corroborated here instead
- [x] 3 candidate-lessons dispositioned: 001 + 002 promoted (`2026-09-18-11-001`, `-002`); 003 discarded (self-declared duplicate of ARGUMENT_NAMING + fix-argparse-rejection coverage)
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- Runs 3–7 staged just-in-time (next: run 3, slice `060`): carry forward the carve
  strategy (lesson `2026-09-18-11-001` — monolith past the file cap carves by
  behaviour cluster) and the splitter discipline (lesson `2026-09-17-15-001`).
- PLAN-177 (leftover gate gaps) is next in queue order with a clear slot.
