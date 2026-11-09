# PLAN-LB-141: Tempdir teardown in the guard-node harness and the executor-mapping tests

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-141-tempdir-teardown-in-test-harnesses.md` and is queued as one row file,
> `queue/PLAN-LB-141.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Two test-support sites create system temp directories that nothing ever removes, and together they
exhausted the inode pool of the `/tmp` tmpfs (1,048,576 inodes) on the operator's machine, so every
`mkdir`/`touch`/build failed with `No space left on device` while the root filesystem still had free
bytes. This plan adds deterministic teardown to both sites and a regression guard, without changing
the worktree-relocation semantics and without touching any production or runtime behaviour.

The operator's analysis of the incident (measured on the machine, 2026-11-09) is the origin of this
spec: about 41,000 `guard-node-*` directories (about 22 inodes each, about 905,000 inodes, about 86
percent of the pool) and about 3,200 `executor-mappings-*` directories (4 inodes each), accumulated
over five days of repeated suite runs from inside plan worktrees under pytest-xdist. The leak was
still live after a manual purge: 1,140 new `guard-node-*` directories appeared in about two hours.

## Deliverables

1. **Harness teardown (`_guard_node_harness.py`).** The directory `_outside_any_worktree()` returns
   from `tempfile.mkdtemp(prefix='guard-node-')` is removed deterministically: on a normal process
   exit, after a failing test, and in every xdist worker. The `/tmp` relocation, its predicate (the
   scratch path contains `/.plan/local/worktrees/`) and the returned path shape stay exactly as they
   are, so the relocated scratch root still does not look like a plan worktree. The 68 `build_harness(`
   call sites across ten test files need no edit if the teardown is owned by the harness module and
   its test-lifecycle wiring; a call-site edit is a finding to record, not the default.
2. **Executor stub directory (`test_execute_script.py`).** `_MAPPED_DIR` is no longer created by a
   module-level `tempfile.mkdtemp` at import time. The three stub files (`manage-files.py`,
   `maven.py`, `test-skill.py`) and the three `_MAP_*` constants the tests and the mapping JSON
   template read are created inside a session-scoped fixture (or an equivalent lifecycle-owned
   construct) whose teardown removes the directory, so a collection error, an aborted run and every
   xdist worker leave nothing behind. The consumer-visible set to keep unchanged: the three notations
   the mapping JSON binds (`plan-marshall:manage-files`, `pm-dev-builder:builder-maven-rules`,
   `test:skill`), each resolving to an EXISTING file (the self-healing existence check in
   `resolve_notation` is why the stubs are real files), with one verification criterion per notation.
3. **Leak regression guard.** A test that fails when a test-support module creates a system temp
   directory with no deterministic removal path: a module-level `tempfile.mkdtemp(` call (runs at
   import, once per pytest process) is always a failure, and a function-level one is a failure unless
   the same function carries a removal (`shutil.rmtree` in a `finally`, a fixture finalizer, or a
   registered teardown). The guard names every site it flags. Every site it flags beyond deliverables
   1 and 2 is fixed in this plan, or recorded with its reason in the landing; the plan does not
   accept a flagged site as debt. A unit-level test also proves deliverable 1 directly: building a
   harness from a scratch path inside a faux `.plan/local/worktrees/` tree relocates it, and the
   registered teardown removes the relocated directory.

## Standing Constraints

- Test-support code only. No file under `marketplace/bundles/` changes, and no production or runtime
  behaviour changes.
- Do not change the relocation semantics: `_outside_any_worktree()` keeps relocating exactly when the
  scratch path resolves inside a plan worktree, and returns the scratch path unchanged otherwise.
  Only deterministic teardown is added.
- Teardown must hold under `pytest -n auto`. A bare `atexit` registration is not assumed to run in an
  xdist worker; the implementing plan proves the chosen mechanism under `-n auto` (see the
  verify-first clause) rather than assuming it.
- No module-level or import-time creation of a temp directory in a test module the plan touches.
- Verification of the leak fix is measured against a RUN-PRIVATE temp root, never against the shared
  system temp directory: the four plans that run concurrently each hold live `guard-node-*` and
  `executor-mappings-*` directories while they run, so "zero such entries in `/tmp`" would fail for a
  correct fix. The measuring run sets `TMPDIR` to a fresh empty directory, runs the suites from
  inside a plan worktree with `-n auto`, and asserts that after the pytest process exits the private
  root holds no `guard-node-*` and no `executor-mappings-*` entry and a total entry count below a
  small stated bound; a second run in the same private root shows no accumulation across runs.
- Out of scope, operator-run, and recorded in the landing as owed rather than done: a
  `systemd-tmpfiles` rule or janitor that reaps stale `guard-node-*` / `executor-mappings-*`
  directories (defence in depth for killed runs, which no in-process teardown can cover), and any
  raise of the tmpfs `nr_inodes` limit (postponement, not a fix). Both live outside the repository.

## Claim Labels

- OBSERVED: `_outside_any_worktree()` returns a bare `Path(tempfile.mkdtemp(prefix='guard-node-'))`
  when the resolved scratch path contains `/.plan/local/worktrees/`, and the module has no
  `shutil.rmtree`, `atexit`, `TemporaryDirectory` or finalizer — read at
  `test/plan-marshall/platform-runtime/_guard_node_harness.py` § `_outside_any_worktree` (line 251)
  and by a content search for `atexit|rmtree` over the file, which matched nothing there.
- OBSERVED: `build_harness()` calls `_outside_any_worktree(scratch)` at line 281, and there are 68
  `build_harness(` call sites across ten files under `test/plan-marshall/platform-runtime/`
  (`test_opencode_enforcement` 22, `test_guard_exact_admissions` 14, `test_guard_shell_constructs` 8,
  `test_guard_hook_parity` 6, `test_guard_cwd_and_worktree_scope` 5, `test_guard_root_session` 4,
  `test_guard_documentation_sweep` 4, `test_guard_documented_commands` 2, `test_guard_wrapper_table`
  2, `test_guard_lane_main_checkout_write` 1) — counted with a content search. The operator's
  analysis said about 60; the measured count is 68 sites in ten files, none needing an edit by default.
- OBSERVED: `_MAPPED_DIR = Path(tempfile.mkdtemp(prefix='executor-mappings-'))` is a module-level
  statement and the stub files are written by a module-level `for` loop — read at
  `test/plan-marshall/tools-script-executor/test_execute_script.py` lines 41-46; `_MAP_MANAGE_FILES`,
  `_MAP_MAVEN` and `_MAP_TEST_SKILL` are read at lines 83-85 (the mapping JSON template) and line 107.
- OBSERVED: `pyproject.toml` declares `pytest-xdist>=3.8` and its comments record 10 xdist workers
  on the measuring host — read at `pyproject.toml` lines 36 and 197-198.
- OBSERVED: the other `tempfile.mkdtemp(` sites in `test/` named by the operator as secondary —
  `test_executor_recovery.py:76` (`pm-recovery-`) opens a `try:` immediately after the call, and
  `test_guard_exact_admissions.py:270` and `:316` (`pm-consumer-lane-`, `pm-consumer-stale-`) pair the
  call with a `try` and a `shutil.rmtree(..., ignore_errors=True)` in `finally`. The `finally` of
  `test_executor_recovery.py` was not read. So these three are not systematic leaks; the three
  `pm-recovery-*` directories on the machine are most likely from killed runs.
- HYPOTHESIS: the remaining bare `tempfile.mkdtemp(` sites listed by the content search may or may not
  leak — `test/conftest.py` lines 1008, 2479 and 2997, `test_doctor_marketplace.py` lines 227 and 443,
  `test_extension_implementations.py:109`, `test_discover_modules.py` lines 825, 982 and 1463,
  `test_maven_pom_parse.py:27`, `test_config_detection.py:32`, `test_runbook_lane.py:837` and
  `_manage_config_build_map_seed_fixtures_surface_norouteextension.py:15` — confirm or refute by reading
  each site's teardown, `test/` files named here (verify-at-outline). Deliverable 3's sweep is the
  authority for which of these are flagged.
- HYPOTHESIS: an `atexit` registration does not reliably run in a pytest-xdist worker, while a
  `pytest_sessionfinish` / `pytest_unconfigure` hook or a session-scoped fixture finalizer does —
  confirm or refute by running a minimal `-n 2` probe that registers each and checking the directory
  afterwards (verify-at-outline).
- HYPOTHESIS: the harness module can own its teardown through a registry of relocated directories
  plus one lifecycle hook in `test/conftest.py`, so no call site changes — confirm or refute at
  `test/conftest.py` § its existing session/worker hooks (verify-at-outline).
- Verify-first clause: before scoping deliverable 1, settle the xdist-worker teardown hypothesis above
  by measurement; a refuted `atexit` assumption selects the lifecycle-hook mechanism, a refuted hook
  assumption loops back to re-scope. Before scoping deliverable 3, run the sweep over `test/` and take
  its flagged-site list, not the HYPOTHESIS list above, as the population.

## Expected Surface

- OBSERVED: `test/plan-marshall/platform-runtime/_guard_node_harness.py` — `_outside_any_worktree`, `build_harness`
- OBSERVED: `test/plan-marshall/tools-script-executor/test_execute_script.py` — the module-level `_MAPPED_DIR` block and its three `_MAP_*` readers
- HYPOTHESIS: `test/conftest.py` — the lifecycle hook that owns the harness registry teardown (verify-at-outline; swept against the tree: the file exists, its hook inventory was not read)
- HYPOTHESIS: `test/plan-marshall/platform-runtime/test_tempdir_teardown.py` — the new regression-guard and relocation-teardown tests (a new file; the directory exists, the name is a proposal)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none of the running plans (PLAN-LB-128 to 131) or the staged ones touch these two
  files. Re-check with `corpus cross-check` before launch, and treat any site Deliverable 3 adds
  beyond this surface as a surface expansion the landing reports.
- Adjacent to: PLAN-LB-137 (`test/plan-marshall/tools-script-executor/test_generate_executor_bootstrap.py`
  and `test_generate_executor_behavior.py`) — same directory as deliverable 2, different files, and
  stays untouched here.
- Urgency: the leak is live while any suite runs from a plan worktree, so each running plan adds to it
  until this ships. It is a blocker in the sense that matters here — a full `/tmp` inode pool stops
  every tool call on the machine, as it did during the ledger land of 2026-11-09.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-141-tempdir-teardown-in-test-harnesses.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
