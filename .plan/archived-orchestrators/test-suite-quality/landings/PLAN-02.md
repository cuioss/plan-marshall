# Landing Analysis: PLAN-02 — Test Standards Compliance

epic: test-suite-quality
workstream: WS-02
pr: #966 — squash-merged as `9903ccac3` (2026-07-21 15:25 UTC)

> Landing record. Every material claim below was corroborated against the real diff,
> the real tree, and real commit history before recording. Two of the operator's own
> conclusions are corrected here on the evidence.

## Deliverable Fidelity vs Spec

The staged spec carried **5** deliverables; **14** shipped. The remediation map's RU-0..RU-9
were absorbed as individual deliverables plus four unplanned additions.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1. Bootstrapping/fixture unification (RU-0, RU-5) | shipped-as-specified | `test/_shared/_input_validation_fixtures.py` created (+197); `test/conftest.py` +44/−18 |
| 2. Standards-compliance refactor of prioritized packages (RU-1..RU-6, RU-8) | shipped-as-specified | 75 files, **3600 insertions / 4699 deletions — net −1099 lines** |
| 3. Redundancy consolidation (RU-2, RU-3, RU-4, RU-9) | shipped-modified | RU-4 shipped with **M4 deferred** (residue, see Follow-Ups) |
| 4. Dead-test + marker hygiene | shipped-as-specified | marker registry relocated to `pyproject.toml:101`; see the `allow_pollution` note below |
| 5. Green quality-gate, no coverage regression | shipped-as-specified | coverage **improved**: line 83.63 → **83.71 %**, branch 78.01 → **78.11 %** |
| — RU-7 discover-modules assertion pruning | **DROPPED — declared infeasible** | no evidence recorded in the landing summary; see Follow-Ups |
| — 11. Marker registry → pyproject.toml | added-unplanned | verified at `pyproject.toml:98-110` |
| — 13. Correct stale conftest allow-list in 3 marketplace standards | added-unplanned | scope leak into marketplace source (docs) |
| — 14. Normalize `_resolve_project_dir_fixtures.py` | added-unplanned | residual helper |

**`allow_pollution` resolved correctly, and not as the scout implied.** The scout found zero
decorator consumers and three autouse fixtures branching on it. PLAN-02 did **not** delete it:
it registered the marker in `pyproject.toml` with an explicit rationale — *"a DELIBERATE ESCAPE
HATCH, retained by design"*. That is the right call. A zero-consumer escape hatch is not dead
code if the guard it disarms is load-bearing, and retaining it keeps PLAN-04's `--strict-markers`
green rather than trading one problem for another.

## Metrics and Anomalies

- Tokens: **3.9 M**; Duration: 3 h 56 m worked / **9 h 56 m wall / 6 h 0 m idle**
- Phase outliers: `6-finalize` burned **1.33 M tokens over 5 h 15 m wall with 4 h 30 m idle** —
  more tokens than `5-execute` (1.15 M) for a phase that ships no deliverables. `3-outline`
  likewise ran 1 h 30 m wall against 32 m worked (58 m idle).
- **Scope growth 5 → 14 deliverables (×2.8).** This is the split-guard presumption
  (~6 deliverables) breached by more than double. It is the direct, measurable cost of the
  no-split decision — recorded as evidence, not as a reproach.
- Review: 2 reviewers, 3 comments, **0 fixes** — nothing actionable found in a 75-file,
  net −1099-line refactor. Thin coverage relative to the surface.
- Self-reported gap: **zero `[DISPATCH]` log lines across nine dispatch boundaries** in
  finalize, because finalize was driven inline. This makes the dispatch-audit's
  inverse-coverage check inoperative for that phase.
- Archive-time warning: `title_reset_failed` (cosmetic).

## Routing and Merge Behavior

- CI/merge: required checks green; merged via merge queue. Worktree removed, main clean.
- **No collision with PR #961.** `execution-accounting-integrity` merged as `5d552d04a`
  *before* PLAN-02, and PLAN-02's `finalize-step-sync-baseline` rebased onto origin/main
  cleanly. The concurrency risk flagged at emit did not materialize.
- Main moved four commits past PLAN-02 during its 9 h 56 m window (#963, #964, #965, #967,
  #968). The long wall-clock, not the disjointness call, is what makes this epic's plans
  collision-prone.

## Reconciliation Actions

- [x] status.json `plans[]` PLAN-02 → `shipped`
- [x] epic.md queue row reconciled
- [x] Baselines & Trend § updated with the post-PLAN-02 measurement
- [x] Open Defect (marketplace quality-gate failure) → **RESOLVED**, with cause identified
- [x] Watch added: RU-4/M4 + RU-7 residue
- [x] Watch added: manifest staleness across mid-flight skill changes (out-of-epic)
- [x] resume_anchor updated; START-HERE regenerated

## Two corrections to the reported conclusions

**1. The open defect is resolved, and I can name the cause.** The baseline recorded
`test_real_marketplace_quality_gate_has_zero_findings` failing at `b591b7d9`; PLAN-02 reports
14 493 passing with no failure, and the test still exists at
`test_doctor_marketplace.py:1038` — so it was fixed, not deleted. The cause is **PR #962**
(`cd931fb63`, 12:45 UTC), *"reconcile promotion-provenance contract with lesson-id lint"* —
it cleaned the `no-lesson-id-in-skill-prose` residue that #958/#924 had left in the marketplace
tree, which is exactly what the real-tree quality gate was tripping on. The defect was never
this epic's to own, and it closed itself while PLAN-02 was in flight.

**2. The lessons-housekeeping ordering is NOT a static manifest bug.** The report diagnosed a
manifest ordering `~87` conflicting with the skill's declared `order: 4`. The evidence says
otherwise: `git show cd931fb63` on the skill shows **`-order: 996` → `+order: 4`** — PR #962
changed that field at **12:45 UTC**. PLAN-02's manifest was composed in phase-4, which ended
roughly **08:20 UTC** (per the phase breakdown, ~2 h 50 m into a run that merged at 15:25).
So the manifest correctly pinned the order that existed when it was composed; #962 then moved
the step into the settle band **mid-flight**, and the running plan kept its stale pinned copy.

The fix therefore is **not** in the manifest composer's ordering logic. The question is whether
a composed manifest should be re-validated against live skill frontmatter at phase-6 entry, and
what a mid-flight `order:` change should do to an in-flight plan. Filed as an out-of-epic watch —
chasing the composer's ordering rules would have been wasted work.

## Follow-Ups

- **RU-7 (discover-modules two-tier assertion pruning) — dropped as infeasible.** No rationale
  was recorded. The map rated it P4 and warned "do NOT blanket-delete (different seams)", so
  infeasible is plausible — but an undocumented drop is not a closed unit. Needs one line of
  justification or requeueing into PLAN-05.
- **RU-4 M4 deferred** — the build-backend consolidation shipped partially. The map already
  scoped RU-4 to the JaCoCo fixture subset and named three out-of-scope fixture families
  (`build-npm` lcov/json, `extension-api` Cobertura/jest, `pm-dev-frontend-cui` lcov/json).
  M4's deferral adds to that residue. Candidate for PLAN-05.
- **PLAN-03 is next and is now cheaper than staged** — PLAN-02 consumed RU-6's plugin-doctor
  scaffold work and the marker registry. PLAN-03's remaining core is the scout's isolation
  findings: the `_test_env` singleton, the 39 always-false skip guards, and the cwd-guard
  asymmetry. Re-read its spec before emitting; parts may already be done.
- **Out-of-epic**: lesson `2026-07-21-17-001` (shared test-helper needs both `sys.path` and
  `mypy_path` registration under `explicit_package_bases`) is owed promotion to
  `pm-dev-python:pytest-testing/standards/`. It is filed against `plan-marshall:build-pyproject`,
  which is the wrong component for a pytest-testing convention.
- **Operator action owed**: `/marshall-steward` + session restart (bundles now 0.1.1179,
  executor regenerated mid-session, 140 scripts).
