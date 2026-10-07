# Test-Suite Cleanup Scout

Epic: `test-suite-quality` · PLAN-01 corrective completion (`test-suite-baseline-and-scout`, D3)

Evidence-backed survey of the tracked test tree across seven hazard classes. Method:
**bounded pattern sweep first, targeted `Read` on hits** — a full read of 621 test modules is
neither affordable nor necessary. Every entry below carries a file path, a line reference, and
a one-line evidence quote. **A dimension with no confirmed hits is reported as clean, not
omitted — a clean verdict is a finding.**

Nothing under `test/**` was written, edited, or deleted by this scout. All findings are
recorded as **leads for PLAN-03**; no remediation is applied here.

## Survey corpus

| Input | Value |
|-------|-------|
| Commit | `b591b7d94ff6a0d10f7f732a1a4f885ac8b09881` |
| Test modules swept | 662 `.py` files under `test/` (621 are `test_*.py`) |
| Single conftest | `test/conftest.py` — 4 autouse fixtures, 2 registered markers |
| Config read | `pyproject.toml` `[tool.pytest.ini_options]`, `[tool.coverage.*]`; `build.py` `cmd_module_tests` / `cmd_coverage` |
| D2 baseline consumed | `test-suite-measurement-baseline.md` (dimension 7 only) |

---

## Dimension 1 — Order-dependent / xdist-sensitive / state-leaking tests

**Verdict: FINDINGS (3 confirmed, 1 systemic).**

### The isolation contract as built

`test/conftest.py` installs four autouse fixtures. Three of them are strong:

| Fixture | Line | Behaviour on leak |
|---------|------|-------------------|
| `_plan_base_dir_sandbox` | `test/conftest.py:630` | redirects `PLAN_BASE_DIR` per test into a `tmp_path_factory` sandbox; also monkeypatches `_config_core.PLAN_BASE_DIR` because the module caches at import time |
| `_credentials_dir_sandbox` | `test/conftest.py:686` | same for `_providers_core.CREDENTIALS_DIR` |
| `_pollution_guard` | `test/conftest.py:558` | **fails loudly** — `pytest.fail(f'Pollution guard: test {request.node.nodeid} leaked into real paths…')` |
| `_restore_cwd` | `test/conftest.py:455` | **silently repairs** — `if os.getcwd() != original_cwd: os.chdir(original_cwd)` |

**1a. Asymmetry: the cwd guard repairs silently while the pollution guard fails loudly.**

> `test/conftest.py:465-466`
> ```python
> if os.getcwd() != original_cwd:
>     os.chdir(original_cwd)
> ```

A test that leaks cwd is repaired and passes; a test that leaks a `.plan/local/` path is
failed with its nodeid. The two guards protect structurally identical hazards with opposite
severities, so cwd leakage is *invisible* — 14 raw `os.chdir()` sites exist and none can
ever be attributed. This is why finding 1b has survived.

**1b. Module-level mutable singleton with raw `os.environ` + `os.chdir`, never torn down —
`test/plan-marshall/tools-script-executor/test_executor_integration.py`.**

> `test_executor_integration.py:197-207`
> ```python
> # Global test environment (created once per test run)
> _test_env = None
>
> def get_test_env() -> ExecutorTestEnvironment:
>     """Get or create the test environment."""
>     global _test_env
>     if _test_env is None:
>         _test_env = ExecutorTestEnvironment()
>         _test_env.setup()
>     return _test_env
> ```

Confirmed by targeted read — this is the single worst isolation site in the tree, on four
counts:

1. **22 tests share one lazily-built singleton** (`get_test_env()` called at lines 220, 233,
   244, 257, 271, 282, 297, 320, 332, 344, 362, 382, 408, 419, 430, 450, 460, 476, 487, 504,
   518). Whichever test runs first pays setup and defines the shared state; the other 21
   inherit it. That is textbook order dependence.
2. **`setup()` bypasses `monkeypatch`** — `os.environ['PLAN_BASE_DIR'] = str(self.plan_dir)`
   (`:67`) is a raw process-global write, so pytest's automatic unwind does not apply. It
   therefore *overrides* the autouse `_plan_base_dir_sandbox` for every subsequent test on
   that worker until `teardown()` runs.
3. **`setup()` calls `os.chdir(self.temp_dir)`** (`:74`) — but the autouse `_restore_cwd`
   restores cwd at the end of the *very first* test, silently invalidating the singleton's
   cwd assumption for tests 2..22. They only pass because `run_executor()` re-supplies
   `cwd=self.temp_dir` explicitly (`:177`).
4. **`cleanup_test_env()` has exactly one occurrence in the entire tree — its own `def` at
   `:210`.** It is never called. The `tempfile.mkdtemp(prefix='executor_test_')` directory
   and the raw `PLAN_BASE_DIR` override leak for the life of the process.

The file carries **no** `xdist_group` marker, so under `-n auto --dist=loadgroup` its 22
tests distribute freely across the 10 workers — each worker independently constructing its
own singleton, and each leaving one behind.

**1c. `xdist_group` is correctly applied — 10 sites, all in `manage-locks`, one group name.**

> `test/plan-marshall/manage-locks/test_build_queue.py:648`
> ```python
> @pytest.mark.xdist_group(name="manage_locks_contention")
> ```

All 10 sites (`test_build_queue.py:648,692,745,812`; `test_locks_core.py:581`;
`test_manage_locks_merge_lock.py:590,645,1225,1289,1338`) use the identical group name and
sit alongside the 13 real-concurrency constructs (`ThreadPoolExecutor` / `threading.Thread`)
in those same three files. The grouping is coherent and `--dist=loadgroup` is hard-wired in
`build.py:237` so the marker cannot be silently defeated. **No lead.**

**1d. `@pytest.mark.allow_pollution` has ZERO consumers.**

The sweep for decorator-position `@pytest.mark.allow_pollution` returns **0 hits across the
whole tree**. All five textual occurrences are prose inside `test/conftest.py` (lines 577,
596, 609, 643, 710 — docstrings and failure messages). Three autouse fixtures each branch on
a marker nobody sets:

> `test/conftest.py:662-665`
> ```python
> if request.node.get_closest_marker('allow_pollution'):
>     # Real-tree tests must see the genuine resolvers — do not redirect.
>     yield
>     return
> ```

The escape hatch is dead code today. That is a *good* state (nothing opts out of isolation),
but it is unguarded: nothing prevents a future test from adding the marker and silently
disabling all three sandboxes plus the pollution guard in one token.

**1e. 43 raw `os.environ[...] = ...` writes bypass `monkeypatch`.** Concentrated in
`test/plan-marshall/manage-logging/test_logging.py` (22 sites, e.g. `:125`
`os.environ['PLAN_BASE_DIR'] = str(plan_base)`), `test/conftest.py` (6), and
`test_executor_integration.py` (2). Most pair with a manual restore, but the restore is
skipped on any exception path — `monkeypatch.setenv` is unconditional.

**1f. `test/plan-marshall/workflow-integration-git/test_prepare_execute.py:240` deliberately
violates the cwd invariant** — `os.chdir(elsewhere)  # invariant violation injected here`.
Intentional and self-documented; relies on `_restore_cwd` to clean up. **No lead**, but it is
the reason `_restore_cwd` cannot simply be converted to a hard failure without an opt-out.

**PLAN-03 leads (D1):**

1. **Convert `test_executor_integration.py`'s module singleton to a session- or
   module-scoped fixture** with real teardown, replacing the raw `os.environ` write with
   `monkeypatch.setenv` and dropping the `os.chdir`. Highest-value single fix in the tree.
2. **Make `_restore_cwd` fail loudly** (symmetric with `_pollution_guard`), with an explicit
   opt-out marker for `test_prepare_execute.py:240`.
3. **Guard the dead `allow_pollution` escape hatch** — either add a test asserting the marker
   has zero consumers, or require a written justification at each future use site.
4. Sweep the 43 raw `os.environ` writes to `monkeypatch.setenv`.

---

## Dimension 2 — Wall-clock / calendar time-bombs

**Verdict: FINDINGS (2 confirmed calendar literals, 4 clock-arithmetic assertions, 1 systemic gap).**

**2a. No clock-freezing library is used anywhere.** The sweep for
`freeze_time|freezegun|time_machine` returns **0 hits**, and `pyproject.toml`'s
`[tool.pyprojectx.main] requirements` list carries no such dependency. Every time-dependent
test therefore asserts against the real system clock.

**2b. Two hard-coded calendar dates in assertions.**

> `test/plan-marshall/ref-toon-format/test_toon_parser.py:129`
> ```python
> assert result['metadata']['created'] == '2025-12-02'
> ```
> `test/plan-marshall/tools-permission-fix/test_permission_fix_behavior.py:162`
> ```python
> assert parsed['timestamp'] == '2025-11-20'
> ```

Both are round-trip assertions against a literal the same test supplies as input, so neither
will break on a date change. They are recorded as **low-severity** — the hazard is the
pattern, not these two instances.

**2c. Four clock-arithmetic assertions with an implicit 60-second budget.**

> `test/plan-marshall/manage-locks/test_build_queue.py:1239` (also `:1250`, `:1272`, `:1292`)
> ```python
> assert active[0]['active_since'] >= time.time() - 60
> ```

These assert "the timestamp was written within the last 60 s". They are correct in principle
but are a **latent flake** under a loaded 10-worker run: the assertion measures wall-clock
elapsed between the fixture write and the assert, which includes any worker preemption. The
same file uses `_STALE_AGE_SECONDS` / `_FRESH_AGE_SECONDS` constants elsewhere
(`:1104`, `:1137`, `:1162`) — the magic `60` is inconsistent with that convention.

**2d. `date.today()` used in 9 filename assertions** —
`test/plan-marshall/manage-logging/test_logging.py:171,361,392,439,629,650,670,694`, e.g.

> `test_logging.py:171`
> ```python
> assert str(date.today()) in path.name
> ```

Each computes the expected log filename from the current date at assert time while the
production code computed it at write time. A test that straddles midnight fails. Probability
is low; determinism is zero. The correct seam is to inject the date, not to re-derive it.

**2e. Suite-wide timeout backstop is configured; no per-test budget approaches it.**

`pyproject.toml:94` sets `timeout = 300` (per-test, SIGALRM on each xdist worker's main
thread — the mechanism choice is documented in the surrounding comment). The sweep found
**zero** `@pytest.mark.timeout(...)` overrides, so every test inherits the 300 s ceiling
uniformly. The largest per-call budgets found are well under it: `test/conftest.py:119`
`timeout=120`, `test/marketplace/targets/test_generate_cli.py:22` `timeout=180`,
`test/plan-marshall/build-pyproject/test_pyproject_build.py:194` `default_timeout=300`. The
last one *equals* the suite ceiling — if that subprocess ever actually ran for its full
budget the pytest-timeout alarm and the subprocess timeout would race.

The suite-wide `timeout = 300` comment claims "the whole suite runs in ~13 min"; the D2
baseline measures **137 s**. The comment is stale by ~6×.

**PLAN-03 leads (D2):**

1. **Adopt a clock seam** (inject a `now` callable, or add `time-machine` / `freezegun`) for
   the 9 `date.today()` filename assertions and the 4 `time.time() - 60` window assertions.
2. Replace the magic `60` in `test_build_queue.py` with the file's existing named-constant
   convention.
3. Reconcile `test_pyproject_build.py:194`'s `default_timeout=300` against the identical
   suite ceiling.
4. Refresh the stale "~13 min" claim at `pyproject.toml:88` against the measured 137 s.

---

## Dimension 3 — Real event loops driving subprocesses

**Verdict: FINDINGS (15 `asyncio.run` sites, 11 real sleeps, 234 subprocess launches).**

**3a. `asyncio.run` is confined to `build-server`, and the low-level loop API is clean.**

15 `asyncio.run(...)` sites, **all** under `test/plan-marshall/build-server/`
(`test_build_server_protocol.py` ×4, `test_marshalld_supervisor.py` ×4,
`test_marshalld_audit.py` ×3, plus one each in `test_acceptance_idempotent_submit.py:73`,
`test_acceptance_reap_survival.py:67`, `test_acceptance_status_toon.py:58`,
`test_interaction_audit_correlation.py:120`).

The sweep for `new_event_loop(` / `get_event_loop(` / `set_event_loop(` /
`run_until_complete(` returns **0 hits** — the deprecated manual-loop API is entirely absent.
`asyncio.run` per test is the correct modern shape. **No lead on the loop API itself.**

One site already demonstrates the deterministic seam this dimension is looking for:

> `test/plan-marshall/build-server/test_interaction_audit_correlation.py:120`
> ```python
> Deliberately does NOT go through ``asyncio.run(daemon.handle_request(...))``.
> ```

**3b. Real `time.sleep()` — 11 literal sites totalling 15.35 s of unconditional wall-clock.**

| Site | Duration | Purpose |
|------|---------:|---------|
| `test/plan-marshall/build-server/test_marshalld_supervisor.py:128` | **10.0 s** | `[sys.executable, '-c', 'import time; time.sleep(10)']` — a child process that sleeps 10 s |
| `test/plan-marshall/plan-retrospective/test_compile_report.py:225` | 1.1 s | mtime-ordering separation |
| `test/plan-marshall/manage-metrics/test_manage_metrics_record_dispatch_boundary.py:155,159` | 1.05 s ×2 | second-granularity timestamp separation |
| `test/plan-marshall/build-server/test_acceptance_daemonize_ppid1.py:33` / `test_marshalld_daemonize.py:34` | 0.5 s ×2 | "let the intermediate session leader exit -> reparent to init" |
| `test/plan-marshall/build-server/test_acceptance_status_toon.py:47` | 0.5 s | child sleeps while status is polled |
| `test/plan-marshall/build-server/test_acceptance_reap_survival.py:55` | 0.4 s | child build simulation |
| `test/plan-marshall/build-server/test_acceptance_daemonize_ppid1.py:50` / `test_marshalld_daemonize.py:63` | 0.1 s ×2 | poll interval inside a `time.monotonic()` deadline loop |
| `test/plan-marshall/manage-locks/test_locks_core.py:642` | 0.05 s | lock-release delay thread |

The 10 s supervisor sleep is **7 % of the entire 137 s suite wall-clock in a single test**.
The two 1.05 s sleeps and the 1.1 s sleep exist purely to cross a **1-second timestamp
granularity boundary** — the canonical case for injecting a clock rather than sleeping.

**3c. Two hand-rolled polling loops** wrap real subprocess launches:

> `test/plan-marshall/build-server/test_marshalld_daemonize.py:59-63`
> ```python
> deadline = time.monotonic() + 10
> while time.monotonic() < deadline:
>     ...
>     time.sleep(0.1)
> ```

Duplicated verbatim at `test_acceptance_daemonize_ppid1.py:46-50`. Correct (monotonic clock,
bounded deadline) but duplicated and untimed-out at the pytest level beyond the global 300 s.

**3d. 234 `subprocess.run/Popen/check_output/check_call` sites** across the tree, concentrated
in `test/plan-marshall/workflow-integration-git/test_git_workflow.py` (23),
`test/plan-marshall/tools-script-executor/test_generate_executor.py` (14),
`test/plan-marshall/workflow-integration-git/test_baseline_reconcile.py` (13),
`test/plan-marshall/phase-2-refine/test_phase_2_refine_manage_config_readonly.py` (11). Most
are legitimate real-resolver E2E (`git init` into a `tmp_path`, executor round-trips). This is
the dominant cost driver behind D2's finding that `plan-marshall` holds 77 % of suite runtime.

**3e. 13 real concurrency constructs** (`ThreadPoolExecutor` ×9, `threading.Thread` ×4) — all
in `manage-locks` (11) and `manage-status/test_orchestrator_store.py:443-444` (2). All the
`manage-locks` ones are `xdist_group`-pinned (D1c). `test_orchestrator_store.py:443` is **not**
pinned:

> `test/plan-marshall/manage-status/test_orchestrator_store.py:443-444`
> ```python
> thread_a = threading.Thread(target=_setter, args=('alpha',))
> thread_b = threading.Thread(target=_setter, args=('beta',))
> ```

Two threads racing a setter, unpinned. It passed in both D2 runs, but it is the only
concurrency site outside the pinned group.

**PLAN-03 leads (D3):**

1. **Cut the 10 s sleep at `test_marshalld_supervisor.py:128`** — the single largest
   attributable time sink found. Replace the sleeping child with a signal/FIFO handshake.
2. **Replace the three ~1 s timestamp-separation sleeps** with an injected clock
   (`test_compile_report.py:225`, `test_manage_metrics_record_dispatch_boundary.py:155,159`).
3. Factor the duplicated `deadline`/`time.sleep(0.1)` poll loop into one shared helper.
4. Audit `test_orchestrator_store.py:443` for an `xdist_group` pin consistent with `manage-locks`.

---

## Dimension 4 — Dead / skipped / xfail-without-reason tests

**Verdict: FINDINGS (39 silent runtime-skip guards; zero unconditional skips; zero xfail).**

**4a. Zero unconditional skips and zero xfail — the clean part.**

| Pattern | Hits |
|---------|-----:|
| `@pytest.mark.skip` (unconditional) | **0** |
| `@pytest.mark.xfail` | **0** |
| `pytest.xfail(...)` | **0** |

There is **no** `xfail` in the tree, so the "xfail without `reason=`" hazard is vacuously
clean. There is no permanently-disabled test. **No lead.**

**4b. The 35 `@pytest.mark.skipif` guards are all legitimate.** Every one carries a `reason=`
and a genuine environment predicate:

> `test/plan-marshall/tools-file-ops/test_tree_copy.py:97`
> ```python
> @pytest.mark.skipif(sys.platform == 'win32', reason='symlink semantics differ on Windows')
> ```
> `test/sync-plugin-cache/test_sync_engine.py:65`
> ```python
> @pytest.mark.skipif(shutil.which('rsync') is None, reason='rsync not on PATH')
> ```

Distribution: `test/sync-plugin-cache/test_staleness_guard.py` (23), `test_sync_engine.py`
(9), `test/plan-marshall/tools-file-ops/test_tree_copy.py` (3). All three predicates are
platform/binary availability. **No lead.**

**4c. FINDING — 39 in-body `pytest.skip(...)` calls that vanish silently, and the D2 baseline
proves every one of them evaluated false.**

The D2 whole-suite runs recorded **0 skipped** out of 14 423. That means all 39 guards were
inert on this host — which is exactly what makes them dangerous: they are load-bearing only
in the environment where they *fire*, and when they fire nothing reports it.

The worst cluster is a single file where 15 tests guard on a **checked-in fixture directory**:

> `test/pm-plugin-development/plugin-doctor/test_analyze.py:77-79`
> ```python
> test_dir = SKILL_STRUCTURE_FIXTURES / 'table-references'
> if not test_dir.exists():
>     pytest.skip('fixture not available')
> ```

Repeated at `test_analyze.py:79,91,103,115,127,139,190,212,230,258,269,281,292,304,315,634`.
If that fixture directory is renamed or moved, **15 tests silently stop asserting anything**
and the suite still reports green. A checked-in fixture is not an environment dependency —
its absence is a bug, and the correct behaviour is to fail.

One guard even documents a *temporal* dependency:

> `test/pm-plugin-development/plugin-doctor/test_analyze.py:230`
> ```python
> pytest.skip('skill directory not found (depends on rename tasks completing earlier)')
> ```

The remaining clusters, by kind:

| Guard reason | Sites | Assessment |
|--------------|------:|-----------|
| `'fixture not available'` / `'skill directory not found'` | 16 (`test_analyze.py`, `test_validate.py:102`) | **should fail, not skip** — fixtures are tracked |
| `'Real marketplace not available'` | 5 (`test_analyze_finalize_step_token.py:439`, `test_analyze_step_configurable_contract.py:461,495`, `test_doctor_marketplace.py:1054,1815`) | legitimate — real-tree dependency |
| `'marketplace/bundles not available in this checkout'` | 5 (`test_body_transforms.py:374,390,459`, `test_dual_emit.py:265`, `test_agent_resolution_poc.py:144`) | legitimate |
| `'real executor not available/present'` | 3 (`test_git_workflow_worktree.py:854`, `test_analyze_manage_invocation_smoke.py:78,106`) | legitimate — needs `/marshall-steward` bootstrap |
| `'Config file missing: …'` | 2 (`test_config_validation.py:78,91`) | **should fail** — tracked config |
| Data-shape guards | 5 (`test_collect_fragments.py:415` `'no domain-contributed retrospective aspects registered'`, `test_fetch_findings.py:214`, `test_audit.py:552`, `test_emitter.py:221,223`, `test_generate_executor_behavior.py:433`, `test_dual_emit.py:269`) | **vacuous-gate risk** — a test that skips when its subject set is empty asserts nothing |

The `'no domain-contributed retrospective aspects registered'` and `'No suppressable rules
configured in sonar-rules.json'` shapes are the **vacuous-gate** anti-pattern: the guard fires
precisely when the thing under test is absent, so the test can never fail for the reason it
exists.

**PLAN-03 leads (D4):**

1. **Convert the 18 tracked-artifact guards to hard failures** (16 fixture/skill-dir sites in
   `test_analyze.py` / `test_validate.py:102`, 2 config sites in `test_config_validation.py`).
   A missing checked-in fixture is a defect, not a skip condition.
2. **Add a skip-count assertion to the suite** — e.g. a CI check that `skipped == 0` on the
   reference platform, so a newly-firing guard becomes visible instead of silent. The D2
   baseline (0 skipped) is the natural enforcement point.
3. **Re-shape the 5 vacuous data-shape gates** to assert the precondition rather than skip on it.

---

## Dimension 5 — Unregistered pytest markers

**Verdict: CLEAN (registration is complete) — with one standing systemic lead.**

**5a. Every marker in use is accounted for.** Full decorator-position inventory across all 662
files:

| Marker | Sites | Status |
|--------|------:|--------|
| `parametrize` | 302 | pytest builtin |
| `skipif` | 35 | pytest builtin |
| `xdist_group` | 10 | **registered** — `test/conftest.py:623-627` |
| `usefixtures` | 3 | pytest builtin |
| `allow_pollution` | **0** | **registered** — `test/conftest.py:616-622` — but has no consumers (see D1d) |

Registration source:

> `test/conftest.py:614-627`
> ```python
> def pytest_configure(config):
>     """Register markers used by the isolation fixtures and pollution guard."""
>     config.addinivalue_line('markers', 'allow_pollution: …')
>     config.addinivalue_line('markers', 'xdist_group(name): pin all tests sharing the same group name to a single xdist worker (requires --dist=loadgroup).')
> ```

**Confirmed clean: there is no unregistered marker in the tree, and no typo'd marker.** The
D2 runs emitted zero marker warnings, which independently corroborates this.

**5b. STANDING LEAD — the clean verdict is unenforced.** Two structural gaps mean a typo'd
marker would still pass silently:

1. `[tool.pytest.ini_options]` (`pyproject.toml:77-94`) declares **no `markers` key** — the
   sweep for `^\s*markers\s*=` in `pyproject.toml` returns 0. Registration lives only in
   `pytest_configure`, which is fine functionally but invisible to anyone reading the config.
2. **`--strict-markers` is absent** — the sweep for `strict-markers|strict_markers` across
   `pyproject.toml`, `build.py`, and the entire test tree returns **0 hits**.
   `addopts = ["-v", "--tb=short"]` (`pyproject.toml:86`) carries neither it nor
   `--strict-config`.

Without `--strict-markers`, `@pytest.mark.xdist_groupp(name=…)` (one typo) registers as an
unknown marker, emits at most a warning, and **silently loses the worker pinning** on the 10
`manage-locks` concurrency tests — the exact tests whose correctness depends on it.

**PLAN-03 leads (D5):**

1. **Add `--strict-markers` to `addopts`.** One-line change; converts the currently-clean
   state from luck into an invariant. Zero migration cost — the sweep proves there is no
   unregistered marker to break.
2. Consider mirroring the two markers into a `markers = [...]` ini key for discoverability
   (or keep `pytest_configure` as the single source and cross-reference it).

---

## Dimension 6 — Warning / deprecation emitters

**Verdict: CLEAN (zero warnings emitted) — with a systemic configuration lead.**

**6a. Both D2 whole-suite runs emitted zero warnings.** Neither the uninstrumented Run A log
nor the coverage-instrumented Run B log contains a `warnings summary` section — pytest omits
that section entirely when no warning is captured. There is **nothing to attribute**: no
`DeprecationWarning`, no `PendingDeprecationWarning`, no
`PytestUnraisableExceptionWarning`, no third-party deprecation, across 14 423 tests.

**6b. The zero is genuine, not suppressed.** The sweep for `filterwarnings` across
`pyproject.toml`, `build.py`, and all 662 test files returns **0 hits**:

- `[tool.pytest.ini_options]` declares no `filterwarnings` key (`pyproject.toml:77-94`).
- No `@pytest.mark.filterwarnings` decorator exists (0 sites).
- No `warnings.simplefilter` / `warnings.filterwarnings` call suppresses anything globally.

So pytest's default filter set was in force and still captured nothing. **This is a real
clean-slate.**

**6c. The only warning-related test machinery is a single legitimate assertion pair.**

> `test/pm-documents/ref-asciidoc/test_asciidoc.py:132-133`
> ```python
> with warnings.catch_warnings(record=True) as recorded:
>     warnings.simplefilter('always')
> ```

This *records* warnings to assert on them, scoped by a context manager. It suppresses nothing
globally. Notably, `pytest.warns(...)` and `pytest.deprecated_call(...)` have **0 sites** —
the tree asserts on warnings exactly once, and via the stdlib rather than the pytest idiom.

**6d. The one non-pytest warning present is a harness artifact, not a code warning.** Every
build log opens with:

> `.plan/temp/build-output/default/python-2026-07-21-073926.log:1`
> ```
> warning: `VIRTUAL_ENV=/Users/oliver/git/plan-marshall/.venv` does not match the project
> environment path `.venv` and will be ignored; use `--active` to target the active
> environment instead
> ```

This is emitted by `uv` before pytest starts — an environment-resolution notice from the
pyprojectx wrapper running inside a worktree, not a test or production warning.

**6e. What "clean" is buying, and what it is risking.** With a zero backlog, any future
dependency bump surfaces its deprecations with a perfect signal-to-noise ratio. But because
`filterwarnings` is unconfigured, warnings are *reported and ignored* rather than *enforced* —
the pinned ceilings in `pyproject.toml:18-38` (`pytest<9`, `pytest-xdist<3.8`, `mypy<2`) exist
precisely to defer major-version migrations, and when one of those ceilings is finally raised
there is no gate to stop a deprecation flood from being normalised.

**PLAN-03 leads (D6):**

1. **Add `filterwarnings = ["error"]` to `[tool.pytest.ini_options]`** with per-item ignores as
   needed. The migration cost is provably **zero today** (0 warnings across 14 423 tests) and
   will never be lower. This converts the clean state into an enforced invariant before the
   `pytest<9` / `pytest-xdist<3.8` / `mypy<2` ceilings are lifted.
2. Prefer `pytest.warns(...)` over the hand-rolled `warnings.catch_warnings` at
   `test_asciidoc.py:132` for consistency, once (1) lands.

---

## Dimension 7 — Slowest tests worth speeding up

**Verdict: FINDINGS — consumed from the D2 baseline; no build was re-run.**

Source: `test-suite-measurement-baseline.md` §5. This dimension **re-runs nothing**.

**7a. Two modules are the entire runtime.**

| Module | pytest session | Share of Σ | Tests | Share of tests |
|--------|---------------:|-----------:|------:|---------------:|
| `plan-marshall` | 103.15 s | **77.2 %** | 12 037 | 83.5 % |
| `pm-plugin-development` | 17.86 s | **13.4 %** | 1 853 | 12.8 % |
| all eight others combined | 12.56 s | 9.4 % | 190 | 1.3 % |

**Any speed-up that does not touch `plan-marshall` is noise.** Cross-referencing D3: the 234
subprocess launch sites cluster in exactly this module (`test_git_workflow.py` ×23,
`test_generate_executor.py` ×14, `test_baseline_reconcile.py` ×13), which is the mechanism
behind the 77 %.

**7b. The single largest attributable cost is cold-cache `pm-plugin-development`.** Three
consecutive runs of the identical module on the identical commit measured **173.35 s →
26.70 s → 17.86 s** — a ×9.7 spread. The cold-run 173 s exceeds the entire warm whole-suite
run (137 s). The driver is the `plugin-doctor` subprocess sweep over the real marketplace
tree — the same subprocess that owns the suite's one failing test
(`test_doctor_marketplace.py:1064`, D2 §6).

**7c. A ~1.4–1.6 s fixed floor dominates the seven small modules.** `pm-dev-oci` runs 2 tests
in 1.40 s; `pm-dev-python` runs 7 in 1.55 s. That floor is interpreter start + collection +
conftest bootstrap. Running the ten modules separately costs 193 s of wrapper wall-clock
against a 137 s whole-suite run — **module-scoped runs are the slower path** for anything but
a single-module change.

**7d. TOOLING LEAD — per-test attribution is unobtainable today.** Three independent blocks:

1. `pyproject.toml:86` — `addopts = ["-v", "--tb=short"]`, no `--durations`.
2. `build.py` `cmd_module_tests` / `cmd_coverage` construct their pytest argv explicitly
   (`cmd_coverage` at `build.py:235-242`) and neither passes `--durations`.
3. The `pyproject_build run --command-args "…"` seam forwards a build *subcommand*, not
   pytest flags — there is no pass-through.

So the finest granularity any architecture-resolved command can produce is **module-level**.
Naming the slowest *tests* — this dimension's actual question — requires a tooling change this
plan deliberately does not make.

**7e. Coverage instrumentation costs ×1.95** (267 s vs 137 s, D2 §2). Not a hotspot to fix,
but a scheduling input: coverage is ~2× the price of a plain test run.

**PLAN-03 leads (D7):**

1. **Add `--durations=25` to `addopts`** (or to `build.py`'s pytest argv). This is the
   unblocking prerequisite for every other D7 lead — without it there is no per-test data.
2. **Then profile `plan-marshall` specifically** — 77 % of runtime, and the D3 subprocess
   density says the cost is real-resolver E2E, not unit tests.
3. **Investigate the `pm-plugin-development` cold-cache ×9.7 cliff** — the first run of a
   fresh checkout or CI job pays 173 s where a warm one pays 18 s. Caching the `plugin-doctor`
   marketplace sweep is likely the single biggest CI win available.
4. **Do not adopt module-scoped runs as a speed strategy** — measured 193 s vs 137 s.

---

## Consolidated PLAN-03 lead list (prioritized)

Ordered by value-per-unit-effort. "Cost" is implementation effort; "Value" is what it buys.

### Tier 1 — one-line config changes, zero migration cost, provably safe today

| # | Lead | Dim | Evidence that cost is zero |
|---|------|-----|----------------------------|
| 1 | Add `filterwarnings = ["error"]` to `[tool.pytest.ini_options]` | D6 | 0 warnings across 14 423 tests, and no existing `filterwarnings` suppression |
| 2 | Add `--strict-markers` to `addopts` | D5 | 0 unregistered markers; full inventory verified |
| 3 | Add `--durations=25` to `addopts` | D7 | unblocks all per-test profiling; no behavioural effect |
| 4 | Refresh the stale "~13 min suite" comment at `pyproject.toml:88` | D2 | measured 137 s |

These four are independent, land together, and convert three separately-verified clean states
into enforced invariants **before** the `pytest<9` / `pytest-xdist<3.8` / `mypy<2` ceilings are
lifted.

### Tier 2 — real isolation defects with a bounded blast radius

| # | Lead | Dim | Site |
|---|------|-----|------|
| 5 | Convert the module-level `_test_env` singleton to a scoped fixture with teardown; drop the raw `os.environ` write and the `os.chdir` | D1 | `test_executor_integration.py:197-215` (22 dependent tests; `cleanup_test_env` never called) |
| 6 | Convert 18 tracked-artifact `pytest.skip` guards to hard failures | D4 | `test_analyze.py` ×16, `test_validate.py:102`, `test_config_validation.py:78,91` |
| 7 | Make `_restore_cwd` fail loudly, with an opt-out for the one deliberate violator | D1 | `test/conftest.py:455-466`; violator `test_prepare_execute.py:240` |
| 8 | Add a `skipped == 0` suite assertion on the reference platform | D4 | D2 baseline records 0 skipped — enforceable today |

### Tier 3 — measurable runtime wins

| # | Lead | Dim | Expected win |
|---|------|-----|--------------|
| 9 | Replace the 10 s sleeping child with a handshake | D3 | `test_marshalld_supervisor.py:128` — ~7 % of suite wall-clock |
| 10 | Investigate the `pm-plugin-development` cold-cache ×9.7 cliff | D7 | up to ~155 s on a cold CI run |
| 11 | Replace 3 timestamp-separation sleeps with an injected clock | D2/D3 | ~3.2 s, plus determinism |
| 12 | Profile `plan-marshall` once `--durations` lands | D7 | 77 % of runtime is in scope |

### Tier 4 — hygiene, no urgency

| # | Lead | Dim |
|---|------|-----|
| 13 | Adopt a clock seam for the 9 `date.today()` and 4 `time.time() - 60` assertions | D2 |
| 14 | Sweep 43 raw `os.environ[...] =` writes to `monkeypatch.setenv` | D1 |
| 15 | Re-shape the 5 vacuous data-shape skip gates to assert their precondition | D4 |
| 16 | Guard the zero-consumer `allow_pollution` escape hatch | D1 |
| 17 | Factor the duplicated `deadline` / `time.sleep(0.1)` poll loop into one helper | D3 |
| 18 | Pin or justify the unpinned thread race at `test_orchestrator_store.py:443` | D1/D3 |
| 19 | Replace the magic `60` in `test_build_queue.py` with the file's named-constant convention | D2 |
| 20 | Prefer `pytest.warns` over `warnings.catch_warnings` at `test_asciidoc.py:132` | D6 |

### Dimensions returning a clean verdict (recorded as findings)

- **D3 event-loop API** — 0 uses of the deprecated `new_event_loop` / `get_event_loop` /
  `run_until_complete` surface; `asyncio.run` per test throughout.
- **D4 dead tests** — 0 unconditional `@pytest.mark.skip`, 0 `xfail` of any kind; all 35
  `skipif` guards carry a `reason=` and a genuine environment predicate.
- **D5 marker registration** — every marker in use is builtin or registered at
  `test/conftest.py:614`; no typo'd or unregistered marker exists.
- **D6 warnings** — 0 warnings emitted, and verified unsuppressed.
- **D1 `xdist_group` usage** — all 10 sites share one coherent group name and sit with the
  concurrency constructs they protect; `--dist=loadgroup` is hard-wired at `build.py:237`.
