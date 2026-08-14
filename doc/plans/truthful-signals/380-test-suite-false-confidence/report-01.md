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
- **D5 — Scope the pollution guard via a marker:** DONE (commit `e29b537`). Introduced the `touches_real_state` marker (registered in `pyproject.toml`; the "complete set of custom markers" comment updated five→six). `pytest_collection_modifyitems` auto-applies it to every `plan_context` user (3330 tests / 189 files); the `_pollution_guard` runs its before/after real-path snapshot only for marked tests and skips it otherwise. **Measured suite time (full `module-tests`, xdist, this cloud runner), same 19623 passed / 14 skipped both runs:** before (guard on every test) **398.59s**; after (guard scoped) **369.09s** — **~29.5s (~7.4%) faster**. The guard was NOT cheap: the delta aligns with the per-test double snapshot removed from ~16,300 non-`plan_context` tests (the `.plan/local/` tree exists in this session — the build harness writes telemetry there — so each snapshot is a real `iterdir`, not a no-op). Single before/after pair, so some is run-to-run variance, but the magnitude matches the guard's mechanism. Refutes the "it is cheap now" claim the plan flagged for measurement.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (production + test
`*.py` changed), so the full path was taken. **`./pw verify` — SUCCESS**: quality-gate
(ruff + mypy production, SPDX, plugin-doctor), test-compile (mypy over 733 test files),
and module-tests (**19623 passed, 14 skipped in 369.09s**, whole-tree pytest) all green.
`UV_HTTP_TIMEOUT=600` was set on every `./pw` call.

## Findings

Verification sub-agent (independent `general-purpose`, read-only) verified all seven
deliverables against `plan.md` and swept beyond the diff for stale claims. Two real
findings, both fixed; one artifact rejected. Per instance:

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | sub-agent (D4) | **Real username `/Users/oliver/git/…` survives in `test/plan-marshall/build-maven/fixtures/log-test-data/{README.md, maven-success-real.log, maven-failure-real.log}`** (14 occurrences) — a fixture tree I never swept. D4's done-when ("no fixture contains a real user's home path") is unconditional; I under-derived the population (the exact "asserted absence is the higher-risk half" trap the plan flagged). | **FIXED.** Normalised `/Users/oliver/git` → `/home/dev/git` in all 3 files. Re-verified: `grep /Users/oliver test/` and `/home/oliver` → **0**. 245 build-maven tests still pass (no test asserts on the paths). |
| 2 | sub-agent (D2) | Stale in-code comment `_build_shared.py:263-265` above `BUILD_FINDING_TYPES` still said a green build "terminalizes every pending finding of these types" — now false for `test-failure`. | **FIXED.** Comment rewritten to state the split (build-error/lint-issue clear on any green build; test-failure only when `tests_run > 0`). |
| 3 | sub-agent (D5) | Report's D5 measurement "IN PROGRESS" / Build-gate "pending". | **REJECTED (artifact).** The agent read the report before the `./pw verify` completed; the before/after measurement (398.59s → 369.09s) was recorded immediately after. Not a code gap. |

The sub-agent verified D1, D2 (core), D3, D6, D7 clean from source and confirmed the
out-of-scope assessment: every `marketplace/bundles/**` change is justified as the D2
finding-clearing path + its publish-the-population plumbing, or a D1 doc update — no
unjustified change to tested code. **Re-dispatch note:** after fixing findings 1-2, the
maven consumers were re-run (245 pass) and the `oliver` absence re-derived to 0; a full
re-verify runs before the merge gate.

CI / PR-review findings: _(pending PR — recorded when they arrive)_

## Reviewer participation

_(pending PR)_

## Cost

_(pending)_

## Contract check (Step 9)

_(pending)_

## What have we learned (Step 9)

_(pending)_

## Residue

- **Generic `/Users/dev/` placeholders remain** in `test/plan-marshall/build-gradle/` (mocks + fixtures) and `test/plan-marshall/build-maven/fixtures/sample-maven-*.log`. These are NOT a D4 done-when violation — `dev` is a generic placeholder, not a real user's home path — and they sit outside the plan's named surface (pm-dev-java, build-npm) and outside the accepted finding. Left unchanged to avoid scope creep. A future consistency pass could unify every build fixture on the single `/home/dev/` root (build-npm was normalised to it as part of the named surface); filed here rather than done.
- **`pyproject.toml` line ~112 still cites "14794 tests"** in the `filterwarnings` rationale; the actual whole-tree count is now 19623 passed + 14 skipped = 19637. This drift is pre-existing (the suite grew independently of this plan) and was NOT introduced by any deliverable here, so it was left alone; noted for whoever next edits that comment.
