# Landing Analysis: PLAN-01 (corrective) — Test-Suite Baseline & Cleanup Scout

epic: test-suite-quality
workstream: WS-01
pr: #960 — https://github.com/cuioss/plan-marshall/pull/960 (squash-merged as `65706bc91`)

> Supplementary landing record. PLAN-01 shipped as PR #955 but dropped two of its four
> Objective items from the staged hand-off; this out-of-band, unqueued corrective plan
> (`test-suite-baseline-and-scout`) produced them. PLAN-01's queue status is unchanged
> (`shipped`) — this record closes the scope gap rather than transitioning a queue item.
> Every claim below was verified against ground truth before recording.

## Deliverable Fidelity vs Spec

The corrective plan's scope came from this epic's two gap watches, not from a staged
`plans/PLAN-NN-*.md` spec. Fidelity is judged against those watches.

| Deliverable (watch) | Verdict | Evidence |
|--------------------|---------|----------|
| Relocate the four `doc/analysis/` docs to gitignored epic-local storage | shipped-as-specified | `git show --stat 65706bc91`: 4 files, 1008 deletions, **zero additions** to the tracked tree — the corpus left permanent docs and was not re-added elsewhere in git |
| Produce the test-suite measurement baseline (duration + coverage + slowest-N + per-module gap map) | shipped-as-specified | `analysis/test-suite-measurement-baseline.md` (17 172 b) present on disk; all six sections populated with sourced values, no placeholders |
| Produce the cleanup-dimension scout (PLAN-03 hardening leads) | shipped-as-specified | `analysis/test-suite-cleanup-scout.md` (33 976 b); seven hazard dimensions, clean verdicts reported as findings rather than omitted |

Epic-local corpus now holds six documents (4 relocated + 2 new) at
`.plan/local/orchestrator/test-suite-quality/analysis/`.

**Independent corroboration of the two sharpest scout claims** (spot-checked rather than
accepted from the narrative):

- `git grep -n cleanup_test_env -- test` → **exactly one hit**, `test_executor_integration.py:210`,
  which is its own `def`. The teardown is genuinely never called. Confirmed.
- `git grep -rn allow_pollution -- test` → **zero decorator applications**. All hits are
  `test/conftest.py` docstrings/messages/branches plus one unrelated docstring reference in
  `test_phase_2_refine_manage_config_readonly.py:33`. Three autouse fixtures branch on a
  marker nobody sets. Confirmed.

## Metrics and Anomalies

- Tokens: 1.7 M
- Duration: 1 h 28 m worked
- Anomalies:
  - `finalize-step-sync-baseline` **rebased onto origin/main and dropped a foreign commit
    `4f40a020c`** — a worktree materialized off a local main that was ahead of origin.
    Caught and corrected in-flight; filed as lesson `2026-07-21-11-002`.
  - `pre-push-quality-gate` had to special-case a docs-only footprint (0 bundles, no pytest
    target) — filed as lesson `2026-07-21-11-003`.
  - Architecture duration estimates forced a real orchestrator hand-off: whole-suite
    `coverage` resolved to `bash_timeout_seconds: 1233` / `exceeds_bash_ceiling: true` /
    `execution_tier: orchestrator` against a **measured 267 s**. Filed as lesson
    `2026-07-21-11-001`.

## Routing and Merge Behavior

- Review: 3 bots responded, **0 comments**. `project:review-retrospective` recorded 0
  pr-comment findings. Clean pass — no triage burden.
- CI/merge: all checks green (verified pre-merge: `overall_status: success`, 10 checks,
  `verify / conclusion` pass, `verify / verify` correctly SKIPPED on the docs-only footprint
  gate). Merged via merge queue as `65706bc91`; worktree removed, `git worktree list`
  confirms only `execution-accounting-integrity` remains; main clean and up to date.
- Surface collisions: none. The corrective plan's footprint was docs-only and did not touch
  `test/**`, so it did not collide with PR #961 (`execution-accounting-integrity`, the
  *plan-optimization* epic) running concurrently.

## Reconciliation Actions

- [x] Baselines & Trend § local-baseline row seeded from the measured numbers
- [x] Watch "Measurement-baseline gap" retired
- [x] Watch "Cleanup-dimension scout gap" retired
- [x] Watch "Analysis corpus relocation" retired; all `doc/analysis/…` path references
      repointed to the epic-local `analysis/` path
- [x] Open Defect opened: pre-existing whole-suite test failure (see Follow-Ups)
- [x] Watch opened: coverage-scope blind spot (342 tests over unmeasured production surface)
- [x] Watch opened: cold-cache variance invalidates naive duration comparisons
- [x] PLAN-02 / PLAN-03 spec ownership notes updated (baseline-first instruction dropped
      from PLAN-02; PLAN-03 now *consumes* the scout list instead of self-surfacing it)
- [x] resume_anchor updated
- [x] START-HERE block regenerated
- [ ] PLAN-01 queue status — **unchanged** (already `shipped`); no transition is correct here

## Follow-Ups

- **Open Defect — the suite is not green.** `test_real_marketplace_quality_gate_has_zero_findings`
  (`test/pm-plugin-development/plugin-doctor/test_doctor_marketplace.py:1064`) fails with
  `quality-gate over the real marketplace tree exited 1 (expected 0)`, 1 902 b of stdout,
  reproduced across four independent observations at baseline commit `b591b7d9`. Not
  investigated by the corrective plan. Recorded as an epic Open Defect; needs confirmation
  at current main head before an owner is assigned.
- **Tier-1 quick wins → PLAN-04** — `filterwarnings = ["error"]`, `--strict-markers`,
  `--strict-config`, `--durations=25`. The baseline proves migration cost is **zero today**
  (0 warnings, 0 skips measured), so the gates can be armed without a cleanup backlog.
  `--durations` is also the prerequisite for per-*test* hotspot attribution, which the
  baseline could not obtain.
- **Isolation defects → PLAN-03** — the `_test_env` singleton (22 tests, raw `os.environ` +
  `os.chdir`, dead teardown), the 39 always-false in-body `pytest.skip` guards (16 keyed on
  checked-in fixture dirs — a rename silently disarms 15 tests while they stay green), and
  the zero-consumer `allow_pollution` marker.
- **Bootstrap waste → PLAN-05** — ~103 s of 312 s per-directory wall-clock is uv/venv
  startup across 14 invocations; whole-suite is already 1.4× cheaper than per-module.
- **Out-of-epic referrals** (recorded, not owned here):
  - Lesson `2026-07-21-11-004` — `finalize-step-lessons-housekeeping` Step 4b.1 instructs
    the `(extends lesson {id})` citation that plugin-doctor forbids. This is the directive
    that turned main red via #958, it is still live, and it duplicates the surface of
    `2026-07-21-10-001`. Belongs to finalize tooling, not this epic.
  - `step_record_mismatched_key` reached its **6th** recurrence; its remediation is PLAN-20
    of the *plan-optimization* epic, in flight as PR #961. Argues for prioritizing it there.
