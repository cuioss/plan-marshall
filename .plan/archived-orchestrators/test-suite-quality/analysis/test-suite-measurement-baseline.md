# Test-Suite Measurement Baseline

Epic: `test-suite-quality` · PLAN-01 corrective completion (`test-suite-baseline-and-scout`, D2)

This document is the epic's **success yardstick**. Every number below is a measured
observation traceable to a named source — a recorded run wall-clock, `.plan/temp/coverage.xml`,
or `pyproject.toml` / `build.py`. No value is estimated, and no value is a placeholder.

---

## 1. Run provenance

| Field | Value | Source |
|-------|-------|--------|
| Commit SHA | `b591b7d94ff6a0d10f7f732a1a4f885ac8b09881` | `git rev-parse HEAD` (worktree `feature/test-suite-baseline-and-scout`) |
| Measurement date | 2026-07-21 | run log filenames under `.plan/temp/build-output/` |
| Host | macOS 26.5.2, arm64 (Apple Silicon), 10 logical CPUs | `os.cpu_count()` / `platform.platform()` |
| Python (test runtime) | 3.14.6 | xdist worker banner in the run logs |
| Python (declared floor) | `requires-python = ">=3.12"`; pyprojectx pins 3.12 | `pyproject.toml:4`, `pyproject.toml:12` |
| xdist workers | **10 workers** (`-n auto` resolved to the CPU count) | run-log worker banner; `build.py` `cmd_module_tests` / `cmd_coverage` |
| xdist distribution | `--dist=loadgroup` (mandatory whenever `-n` is active, so `xdist_group` markers stay worker-pinned) | `build.py:237`, `cmd_module_tests` |
| `marshalld` state | **not running** (`running: false`, `reason: no_pidfile`) for the whole measurement window; the daemon was drained before Run A and left drained through Run C | `manage_build_server status` |
| Test corpus | 621 tracked `test/**/test_*.py` modules; 14 423 collected tests | filesystem count; whole-suite pytest summary |
| pytest addopts | `["-v", "--tb=short"]` — **no `--durations`** | `pyproject.toml:86` |
| pytest timeout | `timeout = 300` (per-test, SIGALRM) | `pyproject.toml:94` |
| Coverage source | `marketplace/bundles` only; `branch = true` | `pyproject.toml:96-98` |
| Coverage threshold | `--cov-fail-under=80` | `build.py:241` (`COVERAGE_THRESHOLD`) |

### Exact resolved executables used

All invocations came from `architecture resolve`; no `./pw`, `uv`, `pytest`, or `mvn`
string was hand-written into any executed command.

| Run | Resolved `executable` | Resolved envelope |
|-----|----------------------|-------------------|
| A — whole-suite tests | `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "module-tests"` | `bash_timeout_seconds: 576`, `execution_tier: per_task` |
| B — whole-suite coverage | `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "coverage"` | `bash_timeout_seconds: 1233`, `exceeds_bash_ceiling: true`, `execution_tier: orchestrator` |
| C — per-module tests (×10) | `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "module-tests {module}"` | e.g. `pm-dev-java` → `bash_timeout_seconds: 150`, `execution_tier: per_task` |

Runs A and B were executed at **orchestrator tier** (detached, orchestrator-owned).
Run C's ten module-scoped invocations are `per_task` and ran inline.

**Coverage-artifact location caveat.** The authoritative Cobertura report for this
baseline is the **worktree-resident** `.plan/temp/coverage.xml`
(`…/worktrees/test-suite-baseline-and-scout/.plan/temp/coverage.xml`, 2.47 MB,
`timestamp` 2026-07-21). The main checkout also carries a `.plan/temp/coverage.xml`, but it
is a **stale, module-scoped artifact** (560 KB, 2026-06-29, `sources` =
`marketplace/bundles/pm-plugin-development`, 73 files). Reading the main-checkout copy
yields a wrong whole-tree picture. Recorded here because it is a live trap for anyone
re-deriving this baseline.

---

## 2. Total wall-clock duration

Two whole-suite runs on the same commit, same host, same worker count, `marshalld` drained
for both.

| Run | Command | Wrapper wall-clock | pytest-reported session | Outcome |
|-----|---------|-------------------|-------------------------|---------|
| **A — uninstrumented** | `module-tests` (whole suite) | **137 s** | 135.26 s (0:02:15) | `exit_code: 1` — 1 failed, 14 422 passed |
| **B — coverage-instrumented** | `coverage` (whole suite) | **267 s** | 264.37 s (0:04:24) | `exit_code: 1` — 1 failed, 14 422 passed |

- **Primary duration yardstick: 137 s** (Run A, uninstrumented, 10 workers).
- **Coverage instrumentation overhead: ×1.95** (267 s / 137 s), i.e. +130 s absolute.
- Both non-zero exits are attributable **solely** to the single pre-existing failure in
  §6 — not to the coverage threshold, which passed (§3).

### Measured observation — architecture duration estimates are badly stale

The `architecture resolve` envelope drives the `per_task` vs `orchestrator` execution-tier
split, so estimate staleness has real routing consequences: an over-estimate pushes a
short build into the orchestrator's detach-and-notify seam unnecessarily, adding a
round-trip and a known-lossy background primitive to a build that would have completed
inline well inside the Bash ceiling.

| Command | Estimate at outline time | Estimate at measurement time | Measured actual | Over-estimate factor |
|---------|-------------------------|------------------------------|-----------------|----------------------|
| `module-tests` (whole suite) | 670 s | 576 s | **137 s** | ×4.9 → ×4.2 |
| `coverage` (whole suite) | 1451 s | 1233 s | **267 s** | ×5.4 → ×4.6 |

The estimates adapted downward between outline and measurement (670→576, 1451→1233) but
remain **~4–5× the measured wall-clock**. The whole-suite `module-tests` estimate crossed
back under the Bash ceiling during this plan (`execution_tier` flipped
`orchestrator` → `per_task`), which demonstrates the feedback loop works — just far too
slowly to be trusted as a routing input at its current convergence rate.

---

## 3. Total coverage

Derived from the worktree `.plan/temp/coverage.xml` (Cobertura, coverage.py 7.15.2),
346 measured source files.

| Metric | Covered | Valid | Rate |
|--------|---------|-------|------|
| **Line (statement)** | 42 518 | 50 840 | **83.63 %** |
| **Branch** | 15 956 | 20 454 | **78.01 %** |

- Configured threshold: `--cov-fail-under=80` (line coverage).
- **Threshold cleared: YES** — 83.63 % ≥ 80 %. The `--cov-fail-under` gate did **not**
  contribute to Run B's non-zero exit; the single test failure in §6 did.
- Branch coverage (78.01 %) is **not** gated by any threshold and sits ~2 points below the
  line-coverage floor. `branch = true` is enabled in `[tool.coverage.run]`, so the number
  is measured but unenforced.

### Coverage-scope caveat (measured gap)

`[tool.coverage.run] source = ["marketplace/bundles"]` — coverage measures **only** the
bundle tree. Three project-owned Python surfaces that the suite *does* exercise are
therefore invisible to every number in this section and in §4:

- `build.py` (the canonical build entry point),
- `marketplace/targets/**` (the multi-target generator) — exercised by 291 tests under
  `test/marketplace/`,
- `.claude/**` scripts — exercised by `test/sync-plugin-cache/` (34 tests),
  `test/finalize-step-deploy-target/` (7), `test/finalize-step-sync-plugin-cache/` (10).

That is 342 tests (2.4 % of the suite) whose production target contributes zero statements
to the 50 840 denominator. The reported 83.63 % is the coverage of the bundle tree, not of
the repository.

---

## 4. Per-module coverage-gap map

One row per architecture module, derived deterministically from `.plan/temp/coverage.xml`
by aggregating each `<class filename=…>` under its first path segment (the coverage
`sources` root is `marketplace/bundles`, so path segment 1 == bundle == architecture
module). Sorted by absolute gap to the 80 % line-coverage threshold, worst first.

| Module | Files | Statements | Covered | Line % | Branches | Br. covered | Branch % | Gap to 80 % |
|--------|------:|-----------:|--------:|-------:|---------:|------------:|---------:|------------:|
| `pm-dev-java` | 2 | 211 | 123 | 58.29 % | 62 | 40 | 64.52 % | **−21.71** |
| `pm-dev-java-cui` | 1 | 24 | 17 | 70.83 % | 4 | 3 | 75.00 % | **−9.17** |
| `pm-documents` | 10 | 812 | 627 | 77.22 % | 338 | 244 | 72.19 % | **−2.78** |
| `pm-dev-frontend` | 2 | 233 | 186 | 79.83 % | 118 | 88 | 74.58 % | **−0.17** |
| `plan-marshall` | 240 | 37 713 | 31 425 | 83.33 % | 14 334 | 11 151 | 77.79 % | +3.33 |
| `pm-plugin-development` | 87 | 11 766 | 10 061 | 85.51 % | 5 576 | 4 410 | 79.09 % | +5.51 |
| `pm-dev-python` | 1 | 24 | 23 | 95.83 % | 6 | 5 | 83.33 % | +15.83 |
| `pm-dev-oci` | 1 | 26 | 25 | 96.15 % | 10 | 9 | 90.00 % | +16.15 |
| `pm-dev-frontend-cui` | 1 | 25 | 25 | 100.00 % | 6 | 6 | 100.00 % | +20.00 |
| `pm-requirements` | 1 | 6 | 6 | 100.00 % | 0 | — | n/a | +20.00 |
| `documentation` | 0 | — | — | — | — | — | — | not measured (no Python source) |
| `default` | 0 | — | — | — | — | — | — | not measured (outside coverage `source`; see §3 caveat) |

Reading notes:

- **Four modules sit below the 80 % threshold** — the whole-tree aggregate clears it only
  because `plan-marshall` (74 % of all statements) and `pm-plugin-development` (23 %) are
  above. `--cov-fail-under` is a whole-tree gate; there is no per-module floor, so a module
  can regress arbitrarily far without tripping any gate.
- The four sub-threshold modules together hold 1 280 statements — **2.5 % of the tree**.
  Their aggregate deficit is small in absolute terms; the gap is a per-module quality
  signal, not a whole-tree risk.
- **Branch coverage is below line coverage in every module except the three trivially
  small ones.** The largest branch-vs-line spread is `pm-documents` (−5.0 points) and
  `pm-dev-frontend` (−5.3 points).
- `pm-requirements` reports 100 % over 6 statements with **zero branches** and has **no
  test directory at all** (§5) — the 6 statements are covered incidentally by imports from
  other modules' tests, not by any test of its own. Treat its 100 % as an artifact.

---

## 5. Slowest hotspots (module granularity)

> **Granularity is module-level, not test-level.** Per-*test* duration attribution is
> **unobtainable** from the architecture-resolved commands: `addopts = ["-v", "--tb=short"]`
> carries no `--durations` (`pyproject.toml:86`), neither `cmd_module_tests` nor
> `cmd_coverage` passes one (`build.py`), and the
> `pyproject_build run --command-args` seam offers no pytest pass-through. Obtaining
> per-test hotspots requires a tooling change (add `--durations=N` to `addopts` or to
> `build.py`'s pytest invocations) that this plan deliberately does not make. Recorded as a
> PLAN-03 lead.

Run C — one `module-tests {module}` invocation per test-bearing architecture module,
`marshalld` drained, inline (`per_task`), sequential.

| Rank | Module | Wrapper wall-clock | pytest session | Tests | Share of Σ session | Outcome |
|-----:|--------|-------------------:|---------------:|------:|-------------------:|---------|
| 1 | `plan-marshall` | 120 s | **103.15 s** | 12 037 | **77.2 %** | pass |
| 2 | `pm-plugin-development` | 30 s | **17.86 s** | 1 853 | **13.4 %** | 1 failed (§6) |
| 3 | `pm-documents` | 17 s | 1.98 s | 99 | 1.5 % | pass |
| 4 | `pm-dev-java` | 12 s | 1.66 s | 35 | 1.2 % | pass |
| 5 | `pm-dev-frontend` | 4 s | 1.58 s | 20 | 1.2 % | pass |
| 6 | `pm-dev-python` | 2 s | 1.55 s | 7 | 1.2 % | pass |
| 7 | `pm-dev-frontend-cui` | 2 s | 1.52 s | 22 | 1.1 % | pass |
| 8 | `pm-dev-java-cui` | 2 s | 1.44 s | 2 | 1.1 % | pass |
| 9 | `default` | 2 s | 1.43 s | 3 | 1.1 % | pass |
| 10 | `pm-dev-oci` | 2 s | 1.40 s | 2 | 1.0 % | pass |
| — | `pm-requirements` | — | — | — | — | **skipped** — `Error: Test directory not found: test/pm-requirements` |
| — | `documentation` | — | — | — | — | **skipped** — no test directory |

Σ pytest session across the ten modules: **133.57 s**; Σ wrapper wall-clock: **193 s**.
The whole-suite Run A session was 135.26 s — i.e. running the ten modules *separately*
costs ~1.4× the whole-suite run in wall-clock, entirely due to per-invocation fixed cost.

Reading notes:

- **`plan-marshall` alone is 77 % of test time and 83 % of test count.** Any suite-level
  speed-up that does not touch `plan-marshall` is noise.
- **A ~1.4–1.6 s fixed floor** is present on every invocation regardless of test count
  (`pm-dev-oci` runs 2 tests in 1.40 s). That floor is interpreter start + collection +
  conftest bootstrap, not test execution — for the seven smallest modules it *is* essentially
  the whole measurement.
- **Wrapper wall-clock exceeds pytest session time by a widening margin for the larger
  modules** (`pm-documents`: 17 s wrapper vs 1.98 s session; `pm-dev-java`: 12 s vs 1.66 s).
  The delta is `uv`/pyprojectx environment resolution, not testing.
- **Cold-cache sensitivity is severe in `pm-plugin-development`.** An earlier sweep on the
  same commit measured 173.35 s, then 26.70 s, then 17.86 s for the identical module — a
  ×9.7 spread across three consecutive runs. `plan-marshall` shows the same effect more
  mildly (152.96 s → 103.15 s, ×1.48). Hotspot numbers here are the **warm-cache** figures;
  the cold-cache first run of `pm-plugin-development` is the single largest one-off cost in
  the suite and is dominated by its `plugin-doctor` subprocess invocations over the real
  marketplace tree.

### Test-count distribution (context for the hotspot table)

The ten architecture modules account for 14 080 of the 14 423 collected tests. The
remaining 343 live in test directories that map to **no architecture module** and are
therefore invisible to every module-scoped `module-tests` invocation — they run only in the
whole-suite sweep:

| Test directory | Tests | Covered by any `module-tests {module}` run? |
|----------------|------:|--------------------------------------------|
| `test/marketplace/` | 291 | no |
| `test/sync-plugin-cache/` | 34 | no |
| `test/finalize-step-sync-plugin-cache/` | 10 | no |
| `test/finalize-step-deploy-target/` | 7 | no |
| `test/test_conftest_discipline.py` | 1 | no |

---

## 6. Observed baseline state (caveat)

> **Everything in this section is recorded as observed state only. Nothing here was
> investigated, diagnosed, or fixed by this plan.** All of it is handed to PLAN-03.

| Category | Count | Notes |
|----------|------:|-------|
| Collected | 14 423 | whole-suite, both Run A and Run B |
| Passed | 14 422 | identical in both runs |
| **Failed** | **1** | see below — identical failure, identical assertion, in both runs |
| Errored | 0 | no collection errors, no worker crashes |
| **Skipped** | **0** | no test was skipped in either whole-suite run |
| xfailed / xpassed | 0 | none reported in either run summary |
| **pytest warnings** | **0** | neither run emitted a `warnings summary` section |

### The single failing test

```
test/pm-plugin-development/plugin-doctor/test_doctor_marketplace.py:1064
test_real_marketplace_quality_gate_has_zero_findings

    assert result.returncode == 0, (
E   AssertionError: quality-gate over the real marketplace tree exited 1 (expected 0).
    stderr: ''
E   assert 1 == 0
E    +  where 1 = ScriptResult(returncode=1, stdout=1902b, stderr=0b).returncode
```

- **Pre-existing**: reproduces identically on the unmodified baseline commit, in Run A
  (uninstrumented), Run B (coverage-instrumented), and the module-scoped
  `module-tests pm-plugin-development` run — four independent observations, same assertion,
  same message. It is not coverage-induced, not xdist-flaky, and not introduced by this plan.
- **Not investigated here.** No hypothesis about the underlying 1 902 bytes of
  `plugin-doctor quality-gate` stdout is offered or tested by this plan.
- It is the **sole** cause of the non-zero exit code on both whole-suite runs. Neither run's
  non-zero exit indicates a coverage-threshold breach (§3) or any other failure.

### Observations that are notable by their absence

- **Zero skips.** The suite has no unconditionally-skipped test that survives a whole-suite
  run — every `skipif` guard present in the tree evaluated false on this host.
- **Zero warnings.** No `DeprecationWarning`, `PytestUnraisableExceptionWarning`, or
  third-party deprecation surfaced. Note that `filterwarnings` is **not** configured in
  `[tool.pytest.ini_options]`, so this is a genuine zero and not a suppressed one. A future
  dependency bump has no existing warning backlog to clear.
- **Zero worker crashes.** The pinned dependency ceilings that exist specifically to prevent
  xdist worker death (`pytest<9`, `pytest-xdist<3.8`, documented at `pyproject.toml:18-29`)
  are holding on Python 3.14.6.

---

## Yardstick summary

The five numbers the epic is measured against:

| Yardstick | Baseline value |
|-----------|---------------|
| Whole-suite wall-clock (uninstrumented, 10 workers) | **137 s** |
| Whole-suite wall-clock (coverage-instrumented) | **267 s** (×1.95 overhead) |
| Line coverage / threshold | **83.63 %** / 80 % — clears |
| Branch coverage (ungated) | **78.01 %** |
| Failing / skipped tests | **1 / 0** out of 14 423 |
