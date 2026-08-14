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

_(updated as the run proceeds)_

- **D4 — Normalise developer paths out of fixtures:** DONE. `/Users/oliver/project` → `/home/dev/project` (3 pm-dev-java logs); `/Users/dev/` → `/home/dev/` (4 build-npm logs). No test asserts on these path strings (verified). Placeholder root `/home/dev/` chosen to avoid the real `/home/user/` on the runner.

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
