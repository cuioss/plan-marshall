# PLAN-03: Propagate Parallel-Plan Test Hardening

epic: test-suite-quality
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-03-propagate-parallel-plan-hardening.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. See `persona-marshall-orchestrator/standards/orchestration-model.md` for
> the tier and hand-off contract.

## Objective

Take the test-hardening patterns already landed by a parallel effort and propagate them suite-wide, so
the hardening is systemic rather than localized to `test/plan-marshall/build-server/`, and repair the
isolation defects the PLAN-01 cleanup scout confirmed. The landed patterns and their commits (all
ground-truth-verified on main, and captured in lesson `2026-07-20-20-001`, scope
`plan-marshall:build-server`): the synchronous-seam-over-`asyncio.run` hang fix (`283f6dcec`); the
CWE-117 control-char log-injection guards, best-effort attribution guard, and gc-format round-trip
guard (`287b13dd4`); the reason/error audit-detail-preservation assertion (`0e4a72917`); and the
wall-clock/calendar **time-bomb** fix (`7eedf98ec`) — a `poll_until` deadline computed from the real
wall clock became a CPU busy-loop once a hard-coded future date passed. The lesson's core insight:
tests green locally on Python 3.14 hung CI on 3.12 via two distinct time-bomb classes (a real event
loop driving a subprocess, and a wall-clock-derived deadline). This plan finds where the same failure
modes exist elsewhere and applies the matching pattern.

## Re-Scope Record (post-#966)

This spec was re-scoped by the orchestrator before emission, after PLAN-02 (PR #966) shipped 14
deliverables against a 5-deliverable spec and absorbed part of the original PLAN-03 surface. Each
claim below was verified against the tree at `8ab5931fc`, not carried over on trust:

**Absorbed by PLAN-02 — REMOVED from this spec:**

- Marker registration / registry hygiene — the registry now lives at `pyproject.toml:101` (`markers = [...]`),
  and `allow_pollution` is registered there as a deliberate, documented escape hatch. Verified.
- RU-6 plugin-doctor scaffold work.

**Reassigned to PLAN-04 — explicitly OUT of scope here** (per the 2026-07-21 sequencing decision):
all Tier-1 `[tool.pytest.ini_options]` config gates — `filterwarnings = ["error"]`, `--strict-markers`,
`--durations=25`, and the stale "~13 min suite" comment refresh. Verified still absent from
`pyproject.toml` (only a comment at `:98` anticipates `--strict-markers`). **This plan must not touch
those keys** — arming `--strict-markers` is PLAN-04's, and `--durations` is PLAN-05's prerequisite.

**Confirmed still present at `8ab5931fc` — the surviving core:**

| Finding | Verification |
|---------|--------------|
| `_test_env` module singleton, 22 dependent tests | `test_executor_integration.py:198-215`; 22 `get_test_env()` call sites; `cleanup_test_env` still has no caller |
| Raw `os.chdir(self.temp_dir)` in singleton setup | `test_executor_integration.py:74` |
| `_restore_cwd` repairs silently | `test/conftest.py:484`, `os.chdir(original_cwd)` at `:494` |
| 39 in-body `pytest.skip(...)` guards across 16 files | exact per-file counts re-measured; `test_analyze.py` ×16, `test_validate.py` ×1, `test_config_validation.py` ×2 |
| 15 `asyncio.run(` sites, all under `build-server/` | unchanged distribution across 7 files |
| The 10 s sleeping child | `test_marshalld_supervisor.py:128` |

## Deliverables

1. **Convert the `test_executor_integration.py` module singleton to a scoped fixture.** Replace
   `_test_env` / `get_test_env()` / the never-called `cleanup_test_env()` with a session- or
   module-scoped fixture carrying real teardown; replace the raw `os.environ['PLAN_BASE_DIR'] = …`
   write (`:67`) with `monkeypatch.setenv` so pytest unwinds it; and drop the `os.chdir(self.temp_dir)`
   (`:74`) — `run_executor()` already supplies `cwd=` explicitly at `:177`. This is the single worst
   isolation site in the tree: 22 tests share one lazily-built singleton, and under
   `-n auto --dist=loadgroup` each of the 10 workers builds and leaks its own.

2. **Make the cwd guard symmetric with the pollution guard.** `_restore_cwd` (`test/conftest.py:484`)
   silently repairs a leaked cwd while `_pollution_guard` fails loudly with the nodeid — structurally
   identical hazards with opposite severities, which is why cwd leakage has been unattributable across
   14 raw `os.chdir()` sites. Make it fail loudly, with an explicit opt-out marker for the one
   deliberate, self-documented violator (`test_prepare_execute.py:240`). Also guard the zero-consumer
   `allow_pollution` escape hatch, which disarms three sandboxes plus the pollution guard in one token
   — assert its consumer set stays empty (or that each future use carries a written justification)
   without removing the registered marker, which PLAN-02 retained by design.

3. **Harden the 39 silent skip guards.** The baseline measured **0 skipped of 14 423**, so every one
   of these evaluated false — they are load-bearing only where they fire, and when they fire nothing
   reports it. Convert the ~19 **tracked-artifact** guards to hard failures (`test_analyze.py` ×16 on a
   checked-in fixture directory, `test_validate.py`, `test_config_validation.py` ×2 on tracked config):
   a missing checked-in fixture is a defect, not a skip condition, and today 15 tests can silently stop
   asserting while the suite reports green. Re-shape the 5 **vacuous data-shape gates** (a test that
   skips when its subject set is empty can never fail for the reason it exists) to assert their
   precondition. Leave the ~13 genuine environment guards (real-marketplace, real-executor,
   `marketplace/bundles` availability) as skips. Add a `skipped == 0` assertion for the reference
   platform so a newly-firing guard becomes visible.

4. **Defuse the wall-clock / real-sleep class.** (a) Apply the `7eedf98ec` pattern: freeze the clock
   seam for the 9 `date.today()` filename assertions (`test_logging.py`) that recompute at assert time
   what production computed at write time, and the 4 `time.time() - 60` window assertions in
   `test_build_queue.py` (also replacing the magic `60` with the file's existing
   `_STALE_AGE_SECONDS`/`_FRESH_AGE_SECONDS` convention). (b) Cut real sleeps: replace the 10 s
   sleeping child at `test_marshalld_supervisor.py:128` — **~7 % of the entire 137 s suite** in one
   test — with a signal/FIFO handshake, and replace the three ~1 s timestamp-separation sleeps
   (`test_compile_report.py:225`, `test_manage_metrics_record_dispatch_boundary.py:155,159`) with an
   injected clock. (c) Factor the duplicated `deadline` / `time.sleep(0.1)` poll loop
   (`test_marshalld_daemonize.py:59-63`, `test_acceptance_daemonize_ppid1.py:46-50`) into one helper,
   and pin or justify the one unpinned thread race at `test_orchestrator_store.py:443` — the only
   concurrency site outside the coherent `manage_locks_contention` group.

5. **Propagate the guard classes from `287b13dd4` / `0e4a72917`.** Audit log-emitting code paths
   reachable from tests for missing CWE-117 control-char log-injection guards (mirroring the
   `run_wait`/`submit` `--job-id` guards) and add regression tests where a real injection sink lacks
   one. Where analogous best-effort guards exist (attribution derivation, gc format round-trips,
   error-detail preservation), add the unmocked round-trip / swallow-failure / detail-preservation
   guards that prove the real writer output survives the real parser. Also apply the `283f6dcec`
   synchronous-seam pattern to any remaining `asyncio.run`-at-loop-close site that admits a job and
   spawns a real subprocess where that subprocess is not the unit under test —
   `test_interaction_audit_correlation.py:120` already demonstrates the target shape.

## Expected Surface

- `test/plan-marshall/tools-script-executor/test_executor_integration.py` (D1).
- `test/conftest.py` (D2) — note PLAN-02 rewrote this file; rebase on the post-#966 shape.
- `test/pm-plugin-development/plugin-doctor/**`, `test/plan-marshall/workflow-shared/test_config_validation.py`,
  and the 16-file in-body-skip set (D3).
- `test/plan-marshall/build-server/**`, `manage-locks/test_build_queue.py`, `manage-logging/test_logging.py`,
  `manage-status/test_orchestrator_store.py`, `plan-retrospective/test_compile_report.py`,
  `manage-metrics/test_manage_metrics_record_dispatch_boundary.py` (D4, D5).
- **`pyproject.toml` is OFF-LIMITS** — the config gates belong to PLAN-04 (see Re-Scope Record).

## Dependencies and Sequencing

- Depends on: PLAN-01 (map + scout locate the targets), PLAN-02 (shipped — rebase on its rewritten
  `test/conftest.py` and `test/_shared/` surface).
- Blocks nothing, but precedes PLAN-04: arming `--strict-markers` / `filterwarnings=["error"]` over a
  tree this plan is still rewriting would invert the dependency.
- Surface disjointness: no plan is currently in flight, so the emit is clear.

## Hand-Off Command

```text
/plan-marshall Repair the confirmed test-isolation defects and propagate the test-hardening patterns already landed by a parallel effort across the plan-marshall test suite. Context is in lesson 2026-07-20-20-001 (scope plan-marshall:build-server): tests green locally on Python 3.14 hung CI on 3.12 via two time-bomb classes. The epic's PLAN-01 cleanup scout confirmed every site below against the tree; re-verify each before changing it. STRICTLY OUT OF SCOPE: do NOT touch [tool.pytest.ini_options] in pyproject.toml — filterwarnings, --strict-markers, --durations and the marker registry belong to a later plan, and arming --strict-markers over the tree this plan rewrites would invert the dependency. Deliver: (1) convert the module-level _test_env singleton in test/plan-marshall/tools-script-executor/test_executor_integration.py:198-215 to a session- or module-scoped fixture with real teardown — 22 tests share one lazily-built singleton, its cleanup_test_env() has never been called, its setup writes os.environ['PLAN_BASE_DIR'] raw (use monkeypatch.setenv so pytest unwinds it) and calls os.chdir(self.temp_dir) which run_executor already makes redundant by passing cwd= explicitly; (2) make the cwd guard symmetric with the pollution guard — _restore_cwd at test/conftest.py:484 silently repairs a leaked cwd via os.chdir(original_cwd) while _pollution_guard fails loudly with the nodeid, so make it fail loudly with an explicit opt-out marker for the one deliberate self-documented violator at test/plan-marshall/workflow-integration-git/test_prepare_execute.py:240, and add a guard asserting the registered-but-zero-consumer allow_pollution escape hatch stays unused (keep the marker — it is retained by design); (3) harden the 39 in-body pytest.skip() guards, all of which the baseline proves evaluated false (0 skipped of 14423) — convert the roughly 19 tracked-artifact guards to hard failures (test/pm-plugin-development/plugin-doctor/test_analyze.py has 16 guarding a checked-in fixture directory, so 15 tests can silently stop asserting while the suite reports green; plus test_validate.py and 2 in test/plan-marshall/workflow-shared/test_config_validation.py on tracked config), re-shape the 5 vacuous data-shape gates that skip precisely when their subject set is empty so they assert their precondition instead, leave the genuine environment guards (real marketplace, real executor, marketplace/bundles availability) as skips, and add a skipped==0 assertion for the reference platform so a newly-firing guard becomes visible; (4) defuse the wall-clock and real-sleep class per commit 7eedf98ec — freeze the clock seam for the 9 date.today() filename assertions in test/plan-marshall/manage-logging/test_logging.py and the 4 time.time()-60 window assertions in test/plan-marshall/manage-locks/test_build_queue.py (replacing the magic 60 with that file's existing _STALE_AGE_SECONDS/_FRESH_AGE_SECONDS convention), replace the 10-second sleeping child at test/plan-marshall/build-server/test_marshalld_supervisor.py:128 (about 7 percent of the whole 137-second suite in a single test) with a signal or FIFO handshake, replace the three roughly 1-second timestamp-separation sleeps in test_compile_report.py:225 and test_manage_metrics_record_dispatch_boundary.py:155,159 with an injected clock, factor the duplicated deadline/time.sleep(0.1) poll loop in test_marshalld_daemonize.py and test_acceptance_daemonize_ppid1.py into one helper, and pin or justify the unpinned thread race at test/plan-marshall/manage-status/test_orchestrator_store.py:443 which is the only concurrency site outside the manage_locks_contention xdist group; and (5) propagate the guard classes from commits 287b13dd4 and 0e4a72917 — audit log-emitting paths reachable from tests for missing CWE-117 control-char log-injection guards (mirroring the run_wait/submit --job-id guards) and add regression tests where a real sink lacks one, add unmocked round-trip, swallow-failure and error-detail-preservation guards for the analogous best-effort paths (attribution derivation, gc format round-trip), and apply the 283f6dcec synchronous-seam pattern to any remaining asyncio.run-at-loop-close site that admits a job and spawns a real subprocess where the subprocess is not the unit under test (test/plan-marshall/build-server/test_interaction_audit_correlation.py:120 already shows the target shape). Rebase on the post-#966 test/conftest.py and test/_shared/ surface. Keep the quality-gate green via the architecture-resolved executor.
```

## Status Trail

- plan_marshall_plan_id: propagate-parallel-plan-hardening
- pr: #977 — merged as `1cfa37044` (2026-07-22, merge queue)
- landing: `landings/PLAN-03.md` — 7 shipped against 5 staged (decomposition of D5, not scope growth); `pyproject.toml` off-limits boundary held
