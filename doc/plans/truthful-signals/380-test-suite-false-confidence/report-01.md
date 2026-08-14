# Run report — 380-test-suite-false-confidence (run 01)

**Date (UTC):** 2026-08-14    **Branch:** claude/test-suite-false-confidence-t9mfb1 (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

Loaded via bundle path (the `plan-marshall` plugin route was not needed):

- `plan-marshall:ref-code-quality`
- `pm-plugin-development:plugin-script-architecture`
- `pm-dev-python:pytest-testing`
- `pm-dev-python:python-core`
- `plan-marshall:persona-implementer`

## GitHub access path

GitHub MCP server (cloud path).

## Claim re-derivation (source of truth for every claim label)

Every count in the plan was a stated LEAD; re-derived from source:

| Plan claim (HYPOTHESIS) | Re-derived verdict |
|---|---|
| Runner treats exit 0 as pass; most files run zero tests under it | **CONFIRMED.** `test/run-tests.py::run_test` (line 116-119) runs `[sys.executable, str(test_file)]` and returns `result.returncode == 0` as success. Only **2** of **765** `test_*.py` files invoke `pytest.main`; only ~12 have any `__main__` block. Plan's "~10 of ~545" LEAD re-derived to **2 pytest-invoking of 765**. |
| Canonical CI path is pytest via build command (developer trap, not CI hole) | **CONFIRMED.** CI runs `./pw verify` → pytest; `run-tests.py` is never invoked by any workflow. |
| Green build clears test-failure findings even when no tests ran | **CONFIRMED from source.** `script-shared/scripts/build/_build_shared.py::cmd_run_common` line 717 gate `if test_summary is None or test_summary.failed == 0:` → `_reconcile_pending_build_findings` clears `('build-error','test-failure','lint-issue')`. Zero-test run → `test_summary is None` → treated as success → clears. No executed-test count ever consulted. |
| Module stubs are guaranteed no-ops (conftest pre-imports real modules) | **CONFIRMED.** conftest lines 187-188 pre-import real `plan_logging`/`run_config`; `sys.modules.setdefault(...)` in **6** files is therefore a no-op. Plan's "five" LEAD re-derived to **6** (`build-npm/test_npm_execute`, `build-maven/test_maven_execute`, `build-pyproject/test_pyproject_execute`, `build-pyproject/test_pyproject_routing`, `build-gradle/test_gradle_execute`, `script-shared/test_build_config_contract`). The 7th `setdefault` (`manage-solution-outline/test_get_module_context.py:67`) registers a REAL module under a custom name — not a dead mock, out of D3 scope. |
| Developer paths in fixtures | **CONFIRMED.** `/Users/oliver/` (real username) in `test/pm-dev-java/fixtures/sample-build-*.log`; `/Users/dev/` (generic placeholder) in `test/plan-marshall/build-npm/fixtures/**`. |
| Pollution guard snapshots real state before/after every test | **CONFIRMED.** `_pollution_guard` (conftest 690-743) is `@pytest.fixture(autouse=True)`; snapshots `~/.plan-marshall/credentials/` + `.plan/local/`. |
| It was already narrowed once for a performance regression | **CONFIRMED.** `_snapshot_real_plan_local` docstring (conftest 660-667) records the recursive-walk regression that "dominated the whole suite's wall-clock". |
| Two overlapping mechanisms mutate the same globals | **CONFIRMED.** Autouse `_plan_base_dir_sandbox` (monkeypatch) vs manual `PlanContext`/`BuildContext` `os.environ`/`_config_core` save-restore. |

## Deliverables

Per deliverable: what was done, in which commit, and its verification state.

- **D1 — Kill the false-green runner:** DONE (commit `771ea1c`). Deleted `test/run-tests.py`. Updated the developer-facing docs that instructed running it (`testing-standards.md` ×5 spots, `cross-skill-integration.md`, `test/pm-dev-frontend/README.md`) to the canonical `module-tests` build command; dropped the stale reference from a `test_detection.py` comment. The conftest/PlanContext references to the runner were cleaned up in D6 (which reworks that region). No code imports the runner, so deletion is safe. Verified: quality-gate green (plugin-doctor accepted the executor invocations).
- **D2 — Finding-clearing requires executed-test evidence:** DONE (commit `85372c6`). `cmd_run_common` in `_build_shared.py` now computes `tests_run` (the parsed executed-test count = `test_summary.total`, 0 when no summary parsed) and passes it to `_reconcile_pending_build_findings`, which clears `build-error`/`lint-issue` on any green build but `test-failure` ONLY when `tests_run > 0`. The population is published: on the success result as the `tests_run` field (added to the `EXTRA_FIELDS` whitelist so TOON and JSON agree) and stamped into the resolution detail. Verified: zero-test green build retains a seeded test-failure finding; a test-running green build clears it and publishes a non-empty population (2081 build-code tests green). Updated `build-api-reference.md` success-output schema (stale-claim sweep).
- **D3 — Delete dead module-stubbing mocks:** DONE (commit `9f70ea5`). Removed the no-op `sys.modules.setdefault('plan_logging'/'run_config', MagicMock(...))` from 6 files (re-derived from the plan's "five" lead) plus their now-unused `sys`/`MagicMock` imports. The 7th `setdefault` (`test_get_module_context.py`) registers a real module under a custom name — not a dead mock, out of scope. Verified: 135 tests in the 6 files pass against the real (pre-imported) modules.
- **D4 — Normalise developer paths out of fixtures:** DONE (commit `63effe4`). `/Users/oliver/project` → `/home/dev/project` (3 pm-dev-java logs); `/Users/dev/` → `/home/dev/` (4 build-npm logs). No test asserts on these path strings (verified). Placeholder root `/home/dev/` chosen to avoid the real `/home/user/` on the runner. Re-derived: only `oliver` was a real username; `dev` was already a placeholder, normalised too for consistency with the named surface.
- **D6 — Retire manual environment save/restore:** DONE (commit `f65ea10`). `PlanContext`, `BuildContext` (conftest) and `EmptyPlanContext` (`test_manage_files.py`) each hand-rolled a save/restore of process-global `PLAN_BASE_DIR`/`PLAN_DIR_NAME` (+ `_config_core` attrs for PlanContext) — a second mechanism overlapping the autouse `_plan_base_dir_sandbox` monkeypatch. Replaced each with a `pytest.MonkeyPatch()` instance reverted atomically by `undo()`. **Interpretation note:** the plan's literal "migrate remaining users to the fixture" (i.e. delete the classes, move ~60+ call sites to fixtures) was NOT taken; instead the classes keep their `with X()` API but now use the fixture's *mechanism* (monkeypatch). Evidence for the deviation: 60+ call sites make wholesale class deletion high-risk churn, and the done-when — "one mechanism owns those globals" — is met because monkeypatch now owns PLAN_BASE_DIR in the autouse sandbox, the `plan_context` fixture, and all three context managers. Verified: 291 context-manager tests pass, zero call-site changes.
- **D7 — Falsifiability control:** DONE (commit `3dbf711`). `test/test_runner_falsifiability.py`: a deliberately failing test reddens the canonical runner (pytest, non-zero exit); a passing test stays green (so the red is a real verdict); the same failing file run AS A SCRIPT exits 0 (documents the retired defect). Verified: 3/3 pass.
- **D5 — Scope the pollution guard via a marker:** IN PROGRESS (see Build gate for the before/after measurement).

## Build gate

_(pending final `./pw verify`)_

## Findings

_(pending verification sub-agent + CI + review)_

## Reviewer participation

_(pending PR)_

## Cost

_(pending)_

## Contract check (Step 9)

_(pending)_

## What have we learned (Step 9)

_(pending)_

## Residue

_(pending)_
