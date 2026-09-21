# Landing Analysis: PLAN-05 — Measurement Protocol & Duration/Coverage Remediation

epic: test-suite-quality
workstream: WS-02
pr: #992 — merged as `a063921b5` (2026-07-23, squash → merge queue)

> Landing record for the epic's capstone. Every material claim corroborated against the real
> diff, the real `pyproject.toml` / `conftest.py`, the protocol doc, and the escalation lesson.
> This is the plan the epic's success criterion was amended around, so the checks were sharp.

## Deliverable Fidelity vs Spec

The amended spec carried 5 deliverables; 8 shipped — a decomposition, not scope growth (the four
coverage modules were split from one "fill the highest-value gaps" deliverable, and reporting was
split from measurement). All accounted for.

| Spec deliverable | Shipped as | Verdict |
|------------------|-----------|---------|
| 1. Per-session `--basetemp`, fix the race not the symptom | 1 | shipped-as-specified |
| 2. Documented protocol with stated detection limit | 2, 8 | **shipped, exemplary** |
| 3. Re-derive hotspots from live per-test data | 3 | shipped-as-specified |
| 4. Fill highest-value coverage gaps | 4–7 | shipped-as-specified |
| 5. Report numbers with confounds stated | 8 | shipped-as-specified |

**All five landing checks written into the resume anchor PASS, verified directly:**

1. **The race was fixed, not silenced.** `filterwarnings = ["error"]` survives at `pyproject.toml:121`
   with **no `rm_rf` ignore entry** — a `git grep` for `rm_rf` in `pyproject.toml` is empty. The fix
   is a per-session `--basetemp` (`build.py` +71, `test/conftest.py` +35) with a bounded-growth prune
   (`PYTEST_BASETEMP_KEEP=3`), since an explicit basetemp forgoes pytest's own keep-last-3 retention.
   The operator's rejected option (a bare ignore) did **not** creep back in.
2. **The detection limit is a first-class deliverable, not a caveat.** `measurement-protocol.adoc:63-74`
   states it in the plainest possible terms: *"A sub-20-second suite-level duration effect is below
   this protocol's noise floor and is undetectable at the suite level"*, and *"a change whose only
   expected effect is a sub-20-second suite-level duration shift should not be claimed from suite
   wall-clock."* This is exactly the discipline the charter was amended to force.
3. **Hotspots re-derived from live data**, not inherited from the four-plan-stale PLAN-01 list — the
   win recorded is a deterministic subprocess-spawn-count reduction in the shared build-test helper,
   not a wall-clock claim.
4. **Numbers reported with confounds** — cache state, sample count, the PLAN-06 toolchain shift, and
   suite growth (14 423 → 14 908) are all stated in the doc.
5. **The honest-negative disposition was exercised and is documented.** `measurement-protocol.adoc:112`:
   *"The suite-level wall-clock delta is not reported as a standalone number… A bounded, or even
   negative, suite-level duration outcome, honestly reported against the stated detection limit, is an
   accepted result of this work."* The epic got the truthful ending it asked for over an
   unfalsifiable win.

## Coverage — the axis that WAS measurable, and it delivered

This is where the epic's demonstrable gain actually lives. All four sub-threshold modules were
re-derived live first (the values differ from the stale baseline, confirming the re-derivation
happened), then lifted:

| Module | Baseline (PLAN-01) | Re-derived live | Shipped | Clears 80 %? |
|--------|-------------------:|----------------:|--------:|:---:|
| `pm-dev-java` | 58.29 % | 56.87 % | **76.78 %** | no — by design |
| `pm-dev-java-cui` | 70.83 % | 64.71 % | **82.35 %** | ✅ |
| `pm-documents` | 77.22 % | 76.35 % | **80.33 %** | ✅ |
| `pm-dev-frontend` | 79.83 % | 76.82 % | **82.40 %** | ✅ |

**`pm-dev-java` stopping at 76.78 % is a correct decision, not a shortfall.** The residual gap is
defensive glue whose only tests would be line-chasing, which the request explicitly excluded in favour
of behavior-focused tests per `pm-dev-python:pytest-testing`. Recorded as a deliberate, principled
stop — the alternative would have been coverage theatre.

## The mid-execute escalation — the epic's discipline held one last time

Deliverable 1's requested basetemp location (`.plan/temp/`, *inside* the repo) broke **40 outside-repo
isolation tests** with a single root cause: once `tmp_path` is a descendant of the real repo, every
upward-walking boundary resolver escapes the fixture and resolves into the real repo, flipping every
"not a git repo / no marketplace / returns None / fails closed" negative assertion to a positive.

The resolution chose **hold-the-line**: migrate all 40 tests to an `outside_repo_dir` fixture
(`conftest.py:909`, now used across 23 files) rather than weaken any assertion or move basetemp back
out. Corroborated: the fixture exists and the diff touches exactly the boundary-test modules the
lesson enumerates. **No assertion was weakened** — the isolation guarantee those tests exist to prove
is intact. Captured as lesson `2026-07-23-10-001` (`pm-dev-python:pytest-testing`).

This is the same "fix the boundary, not the assertion" instinct that ran through the whole epic, and
it is the *inverse* of the PLAN-06 over-scope error: here the escalation's scope (40 tests, 14
modules) was sized from the actual failure enumeration, not from a symptom count.

## Metrics and Anomalies

- Tokens **2.9 M**; **3 h 13 m worked / 12 h wall** — the wall is idle-inflated by ~8 h 50 m of
  operator-hold (the escalation), not machine time. The 2.9 M crosses the complex-track anchor,
  driven by the 40-test migration and the iterative coverage-fill loop — both legitimate, both the
  direct cost of the hold-the-line decision.
- Review: **0 actionable comments**. **Fourth consecutive plan** with near-zero bot yield on this
  epic's shape — the "bots find nothing in test-refactor work" watch is now firmly established across
  the whole campaign.
- Self-review: 115 candidates, clean; `simplify`: 1 edit.
- Suite: **14 908 pass**, 378 s CI, 0 warnings — the armed gate held through the whole plan.

## Routing and Merge Behavior

- Squash-merged at `a063921b5`; main up-to-date, worktree removed, tree clean, plan archived.
- **Manifest predated PR #990** (which reordered `preference-emitter`), so a couple of finalize steps
  ran in the older order — handled without incident. This is a fresh instance of the same
  manifest-staleness-vs-mid-flight-skill-change class this epic first surfaced at PLAN-02 (the
  lessons-housekeeping ordering). Recorded, out-of-epic.

## Reconciliation Actions

- [x] status.json `plans[]` PLAN-05 → `shipped`
- [x] epic.md queue row reconciled
- [x] Baselines & Trend § — final coverage row added
- [x] Open Defect (filterwarnings local non-determinism) → **RESOLVED** by deliverable 1
- [x] resume_anchor updated; START-HERE regenerated
- [x] Epic is now fully drained — ready for `close`

## Follow-Ups (carried into close)

- Out-of-epic, need fix plans not lessons: the finalize `[DISPATCH]`-audit gap + dropped-findings
  piggyback; the two retrospective-tooling bugs (`2026-07-22-22-001/002`); and now a fresh
  manifest-staleness instance (#990 reorder).
- Unowned epic residue: RU-4/M4 + RU-7 (never resolved by any plan); the coverage-scope blind-spot
  decision (bundle-tree-only `source`) was left to PLAN-05 but not actioned — the plan filled
  in-scope module gaps rather than widening the coverage denominator. Record honestly: this decision
  was **not** taken.
- Operator: `marshal.json` config-stale (provisioned 0.1.1192 vs installed 0.1.1198) — `/marshall-steward`.
