# Landing Analysis: PLAN-01 — Scrupulous Test-Suite Analysis

epic: test-suite-quality
workstream: WS-01
pr: #955 (squash-merged to main, 4c4b8cb92)

> Landing record for one shipped plan. Written by the `analyze` verb after
> verifying claims against ground truth (actual code, artifacts, PR state).

## Deliverable Fidelity vs Spec

Verified against the merged tree: all four documents exist under `doc/analysis/`
and their content matches the spec's intent. Ground truth checked: `git log`
confirms PR #955 squash-merged at 4c4b8cb92; the four docs read on disk.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| Redundancy report | shipped-as-specified | `doc/analysis/test-suite-redundancy-report.md` — near-duplicate/overlapping clusters (extension-security-profile mirrors ×6 bundles, GitHub/GitLab CI-provider mirrors, build-backend coverage parallelism, per-script input-validation triplication) + redundant-assertion patterns, each with a consolidation candidate |
| Fixture & bootstrapping inventory | shipped-as-specified (+corrected premise) | `doc/analysis/test-fixture-bootstrapping-inventory.md` — single `test/conftest.py` + all shared-helper modules; corrected the request premise (build_test_helpers.py / discovery_test_helpers.py DO exist; _pm_input_validation_fixtures.py / _resolve_project_dir_fixtures.py catalogued with the real on-disk set) |
| Shared-fixture unification proposal | shipped-as-specified | `doc/analysis/test-fixture-unification-proposal.md` — single-root-vs-package-scoped decision (honors conftest.py naming rule), helper merge map M1–M5, per-consumer migration notes |
| Prioritized remediation map | shipped-as-specified | `doc/analysis/test-suite-remediation-map.md` — 10 remediation units tagged standards-compliance vs hardening-propagation, prioritized, surface-disjoint parallelizable pairs flagged |

Note on the emit-time observation: the staged Hand-Off Command carried 4 of the
Objective's 5 items (dropped the measurement baseline and the cleanup-dimension
scout). The plan shipped the 4-doc map; the measurement baseline (coverage %,
wall-clock, slowest-N hotspots, per-module gap map) and the explicit
cleanup-dimension scout were NOT produced as separate artifacts. This is a
known scope gap carried into WS-02 — see Follow-Ups.

## Metrics and Anomalies

- Tokens: 2.4M total (per operator finalize summary)
- Duration: 2h45m wall time
- Anomalies: `plan-retrospective` step skipped (infrastructure API cutoff,
  advisory/non-blocking) — no quality-audit report produced for this plan.

## Routing and Merge Behavior

- Review: 7 bot comments on the analysis docs → 5 fixed (documentation-consistency
  defects), 2 accepted. One bot's suggested path prefix was itself wrong; triage
  verified against the real tree and used the correct `test/plan-marshall/` prefix.
- CI/merge: green; squash-merged via the merge queue. No rebase conflicts, no
  re-verify signals. Surface-disjoint from all other work (analysis-only) — no
  collisions to feed forward to pairing decisions.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated — PLAN-01 → shipped, pr=#955, landing recorded
- [x] epic.md queue reconciled from status.json (via resume-summary regeneration)
- [x] Watch opened: measurement-baseline + cleanup-dimension-scout scope gap (see Follow-Ups)
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- **Measurement-baseline gap** → WS-02 gate. The epic's stated success criterion is
  measurable gains in BOTH duration and coverage relative to a baseline that was
  never captured. The first WS-02 remediation plan (PLAN-02) must capture the
  coverage %, wall-clock duration, slowest-N hotspots, and per-module coverage-gap
  map before mutation, or the epic has no yardstick. Recorded as a Watch.
- **Cleanup-dimension scout gap** → the PLAN-03 hardening leads (order-dependent /
  xdist-sensitive tests, calendar-derived CI time-bombs, unregistered markers,
  warning emitters) were not scouted as a discrete list. PLAN-03 (parallel-plan
  hardening propagation) must surface these itself rather than consume a ready list.
- **plan-retrospective skipped** — advisory; re-run later if the retrospective is wanted.
- **marshal.json stale** (config 0.1.1152 vs installed 0.1.1165) — executor
  auto-regenerated at finalize; operator owes `/marshall-steward` to reconcile
  provisioning stamps. Outside this epic's tree — noted, not actioned here.
