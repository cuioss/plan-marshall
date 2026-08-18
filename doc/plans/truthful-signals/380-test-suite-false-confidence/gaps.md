# Gaps — 380-test-suite-false-confidence

**Source:** verification.md (same directory)   **Open items:** 6

## G1 — Count only executed tests in `tests_run`, not skipped ones

- **Kind:** bug
- **Severity:** high
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py:751` — `cmd_run_common`; the population it reads is defined at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_parse.py:193` (`UnitTestSummary.total`) and produced at `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_parse.py:539`.
- **What is wrong:** D2 gates the clearing of a `test-failure` finding on `tests_run > 0`, described throughout as "the executed-test count". `tests_run` is `test_summary.total`, and both summary producers define `total = passed + failed + skipped`. Executed against the real parser: `_extract_pytest_summary('===== 5 skipped in 0.42s =====')` returns `UnitTestSummary(passed=0, failed=0, skipped=5, total=5)`, so a green run in which no test body ran reports `tests_run = 5` and takes the clearing branch.
- **Why it matters:** a green build that executed nothing but skips destroys a true, already-recorded `test-failure` finding — the exact mechanism D2 exists to stop, narrowed rather than closed. Reachable whenever a scoped `module-tests` run collects only platform- or condition-skipped tests.
- **Fix:** in `cmd_run_common`, compute `tests_run = test_summary.passed + test_summary.failed` (or add an explicit `executed` property to `UnitTestSummary` and use it), leaving the published `tests_run` field defined as *executed*, and update the `_reconcile_pending_build_findings` docstring, the `_build_format.py` `EXTRA_FIELDS` docstring and `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-api-reference.md:88-93` to say so. Add a test in `test/plan-marshall/build-pyproject/test_build_findings_store.py` driving `cmd_run_common` with a parser returning `UnitTestSummary(passed=0, failed=0, skipped=5, total=5)` and asserting the seeded `test-failure` finding survives.
- **Done when:** a green build whose summary is skips-only leaves a pending `test-failure` finding pending, and the published `tests_run` on that run is 0.
- **Module/topic:** `plan-marshall:script-shared` build finding reconciliation (D2).

## G2 — Extend the `touches_real_state` predicate beyond the `plan_context` fixture

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `test/conftest.py:733-735` — `pytest_collection_modifyitems`
- **What is wrong:** the marker is applied only when `'plan_context' in item.fixturenames`. `test/conftest.py:718-722` says a state-driving test without that fixture "opts in by carrying the marker explicitly", but `grep -rn "mark.touches_real_state" test/` returns **0** — nothing takes that route. Six files drive plan/build state through the `PlanContext` / `BuildContext` context managers with no mention of `plan_context` (`test/plan-marshall/tools-script-executor/test_execute_script.py`, `test/plan-marshall/build-npm/test_npm_discover_modules.py`, `test/plan-marshall/build-npm/test_npm.py`, `test/plan-marshall/build-npm/test_npm_discover.py`, `test/plan-marshall/build-pyproject/test_pyproject_build.py`, `test/plan-marshall/build-gradle/test_gradle_discover_modules.py`), and four more override `PLAN_BASE_DIR` by hand (see G3). None of them is marked, so `_pollution_guard` (`test/conftest.py:960`) skips its before/after snapshot for all of them.
- **Why it matters:** the guard was narrowed away from precisely the tests that bypass or override the autouse sandbox — the population where a real-tree leak is actually possible and where the backstop had its remaining value. A future leak from those tests would now pass silently.
- **Fix:** broaden the predicate in `pytest_collection_modifyitems` so a test is marked when it requests `plan_context` **or** its module references `PlanContext` / `BuildContext` / `EmptyPlanContext` / writes `PLAN_BASE_DIR`; alternatively mark those files explicitly with `pytestmark = pytest.mark.touches_real_state`. Add a collection-time test asserting each of the named files yields marked items.
- **Done when:** every test that enters `PlanContext`/`BuildContext` or sets `PLAN_BASE_DIR` itself collects with `touches_real_state`, and the re-derived marked count is reported alongside the total.
- **Module/topic:** `test/conftest.py` — pollution-guard scoping (D5).

## G3 — Finish retiring the manual `PLAN_BASE_DIR` save/restore

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `test/plan-marshall/manage-logging/test_logging.py` (22 sites, e.g. `:175`/`:180`), `test/plan-marshall/build-maven/test_maven_run.py:48-56` — `mock_maven_project`, `test/plan-marshall/build-npm/test_npm_run.py:39-47`, `test/plan-marshall/script-shared/test_build_parse.py:152-159`
- **What is wrong:** D6's done-when is "one mechanism owns those globals". At `fa452e0c~1`, `git grep -c "os.environ['PLAN_BASE_DIR'] = " -- test/` listed six files; the run converted two (`conftest.py`, `test_manage_files.py`) and left four. All four still hand-roll the mutation at HEAD (28 sites total). `test_logging.py` is the worst shape: 22 tests finish with `del os.environ['PLAN_BASE_DIR']`, which removes the variable rather than restoring the autouse sandbox's value, so anything later in that test body resolves the real repository tree. Separately `test/plan-marshall/manage-providers/test_list_providers.py` assigns `_config_core.PLAN_BASE_DIR` / `MARSHAL_PATH` directly at 24 sites with no restore at all (12 predate this plan).
- **Why it matters:** two mechanisms still mutate the same globals, which is the condition D6 was written to remove; combined with G2 the pollution guard no longer watches these tests, so the isolation invariant is neither enforced structurally nor checked.
- **Fix:** replace each manual save/restore with the `monkeypatch` fixture (or a `pytest.MonkeyPatch()` instance reverted by `undo()`), matching `PlanContext`/`BuildContext`; in `test_list_providers.py` replace the raw `_config_core.PLAN_BASE_DIR = …` / `MARSHAL_PATH = …` assignments with `monkeypatch.setattr`. Then add a guard test (or a plugin-doctor/lint rule) asserting `os.environ['PLAN_BASE_DIR'] = ` and `_config_core.PLAN_BASE_DIR = ` do not appear under `test/`.
- **Done when:** a tree-wide grep for direct `os.environ['PLAN_BASE_DIR'] =` / `del os.environ['PLAN_BASE_DIR']` / `_config_core.PLAN_BASE_DIR =` under `test/` returns zero, and the suite is still green.
- **Module/topic:** test harness — environment sandbox ownership (D6).

## G4 — Remove the two conftest comments that still describe the deleted module stubs

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `test/conftest.py:188-190` (the pre-import rationale) and `test/conftest.py:1152-1154` (inside `_neutralize_daemon_routing`'s namespace helper)
- **What is wrong:** both comments describe `sys.modules.setdefault('plan_logging', MagicMock(...))` as a pattern test modules currently use — line 1153 says "the `MagicMock` module stand-ins several test modules install via `sys.modules.setdefault`". D3 deleted every one of them: `grep -rn "sys.modules.setdefault" test/` now returns only these two comments, and the remaining `sys.modules[name] = …` assignments in the suite register real modules, not mocks.
- **Why it matters:** a reader looking for the stubs to understand or extend the isolation machinery finds nothing, and may re-introduce the pattern believing it is sanctioned — the same "a claim the code does not honour" defect D3 removed.
- **Fix:** rewrite `:188-190` to state the pre-import as a defensive ordering guarantee without asserting current stub usage, and rewrite `:1152-1154` to justify the `isinstance` check on its own terms (it filters non-dict namespaces) rather than by reference to stand-ins that no longer exist.
- **Done when:** no comment under `test/` asserts that test modules install `MagicMock` stand-ins via `sys.modules.setdefault`.
- **Module/topic:** `test/conftest.py` — module-stub removal follow-through (D3).

## G5 — Correct the residue entry's placeholder and population

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/380-test-suite-false-confidence/report-01.md` — § Residue, first bullet
- **What is wrong:** the bullet says generic `/Users/dev/` placeholders remain in `test/plan-marshall/build-maven/fixtures/sample-maven-*.log`. Those files contain `/Users/test/`, not `/Users/dev/` — `git grep -l "/Users/dev" fa452e0c -- test/plan-marshall/build-maven/` matches nothing, while `/Users/test/` appears 7/6/3/2 times in `sample-maven-failure.log`, `sample-maven-success.log`, `sample-maven-javadoc.log`, `sample-maven-openrewrite.log`. The bullet also omits three files that do carry `/Users/dev/`: `test/plan-marshall/platform-runtime/test_pretooluse_gate.py` (6), `test_claude_pretooluse_hook.py` (2), `test_claude_pretooluse_capture.py` (2).
- **Why it matters:** the bullet is the handover for a future consistency pass; following it verbatim searches for the wrong string in build-maven and misses three files entirely.
- **Fix:** amend the residue bullet to name `/Users/test/` for the build-maven sample logs, and add the three `platform-runtime` test files to the `/Users/dev/` list. A single unification pass onto one placeholder root (`/home/dev/`) across all four trees settles it.
- **Done when:** every fixture and test placeholder path under `test/` resolves to one declared placeholder root, and the residue bullet names the same set the tree contains.
- **Module/topic:** test fixtures — placeholder-path normalisation (D4 follow-on).

## G6 — Refresh the stale test count in the `filterwarnings` rationale

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `pyproject.toml:112`
- **What is wrong:** the comment reads "whole-tree run of all 14794 tests under the flags above emits ZERO warnings". Re-derived at HEAD, collection reports **20974** tests. The report declared this as residue and left it, correctly noting it is pre-existing drift.
- **Why it matters:** the zero-warnings claim is anchored to a population that no longer exists, so a reader cannot tell whether the claim was ever re-checked against the current suite.
- **Fix:** re-run the whole-tree suite under those flags, confirm zero warnings, and replace the number with the freshly derived count — or drop the number and state the property without a population figure.
- **Done when:** the comment either names a count that matches a re-derivation at the time of the edit, or states the zero-warnings property without a count.
- **Module/topic:** `pyproject.toml` — pytest configuration comments.
