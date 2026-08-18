# Verification — 380-test-suite-false-confidence

**Verified against:** commit `dcaf8aa56d0cba9f20245e148125b508754b085a`   **Landed as:** PR #1229, commit `fa452e0cff17f4d7e884d4e5cdcff0586594d810`   **Verdict:** implemented-with-gaps

## Method

What was actually done, in order:

- Read `plan.md` and `report-01.md` in full; extracted all seven deliverables with their
  *Done when:* conditions, the Out-of-scope block, the Expected surface, the Claim-labels table
  and the Verification section.
- Located the landed commit with `git log --oneline --all --grep '#1229'` → `fa452e0c`; read
  `git show --stat fa452e0c` (32 files, +641/−400) and the per-file diffs for
  `_build_shared.py`, `_build_format.py`, `build-api-reference.md`, `testing-standards.md`,
  `cross-skill-integration.md`, `test_manage_files.py`, `test_detection.py`,
  `test/pm-dev-frontend/README.md`.
- Opened at HEAD: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py`
  (lines 260–270, 427–478, 740–782), `.../build/_build_format.py` (EXTRA_FIELDS + docstring),
  `.../build/_build_parse.py` (`UnitTestSummary`, `extract_test_summary`),
  `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_parse.py`
  (`_extract_pytest_summary`), `test/conftest.py` (lines 186–192, 700–740, 925–1050, 1531–1615,
  1929–2012), `test/test_runner_falsifiability.py` (whole file),
  `test/plan-marshall/build-pyproject/test_build_findings_store.py` (lines 230–485),
  `test/plan-marshall/manage-files/test_manage_files.py` (EmptyPlanContext),
  `pyproject.toml` (marker block, lines 155–210).
- Ran tests (`UV_HTTP_TIMEOUT=600 uv run python -m pytest … -o addopts="" -q`):
  - `test_build_findings_store.py` + `test_cmd_run_common.py` + `test_runner_falsifiability.py` → **55 passed**.
  - `test_runner_falsifiability.py` alone, verbose → **3 passed in 0.58s**; independently timed a
    bare `python -m pytest` subprocess at 0.27s to confirm the 3 subprocess launches are real, not stubbed.
  - `test/plan-marshall/{manage-files/test_manage_files.py,build-npm,build-maven,build-gradle,script-shared,build-pyproject}`
    → **1975 passed in 109.55s**.
- **Executed** (not read) the D2 publish path:
  `success_result(..., tests_run=42)` → `format_toon` emits `tests_run: 42`; the zero case emits
  `tests_run: 0` (published, not omitted).
- **Executed** the pytest summary parser:
  `_extract_pytest_summary('===== 5 skipped in 0.42s =====')` →
  `UnitTestSummary(passed=0, failed=0, skipped=5, total=5)`; `'no tests ran in 0.01s'` → `None`.
- **Mutation check (D2, the highest-risk guard).** Confirmed
  `git diff --quiet -- .../_build_shared.py` exited 0 (file not concurrently modified), saved the
  file bytes to the scratchpad, changed `if tests_run > 0:` → `if tests_run >= 0:`, re-ran
  `test_build_findings_store.py` → **2 failed, 29 passed**
  (`test_reconcile_retains_test_failure_when_no_tests_ran`,
  `test_green_build_zero_tests_retains_seeded_test_failure_end_to_end`). Restored from the saved
  bytes with `cp`; `git diff --quiet` exits 0 again and `git diff --stat` is empty. No
  `git checkout`/`restore`/`stash` was used. No other file was mutated.
- Re-derived counts at HEAD: `sys.modules.setdefault` in `test/` = 0 (2 prose mentions remain in
  `conftest.py`); `/Users/oliver` or `/home/oliver` anywhere under `test/` = 0; pytest markers
  registered in `pyproject.toml` = 6 (parsed with `tomllib`); tests carrying
  `touches_real_state` = **4063 of 20974** collected; `os.environ['PLAN_BASE_DIR'] = ` assignment
  sites in `test/` = 28 across 4 files; `_config_core.PLAN_BASE_DIR = ` direct assignments = 24
  (all in `test_list_providers.py`).
- Re-derived the D1 claim counts at `fa452e0c~1` via `git ls-tree` / `git grep`:
  769 `test_*.py` files, **2** invoking `pytest.main`, **13** with any `__main__` block.
- Superseded-vs-gap checks with `git log --oneline -- <file>` on
  `test/run-tests.py`, `test_get_module_context.py`, `test_list_providers.py`,
  `test_maven_run.py`.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1 | Kill the false-green runner | Deleted, or shells out to pytest per file | Yes | Yes | Yes | Yes | `test/run-tests.py` absent at HEAD; `git log -- test/run-tests.py` last touched by `fa452e0c`. Tree-wide grep for `run-tests.py`/`run_tests.py` → only `test/test_runner_falsifiability.py:5,81` (historical prose) and an unrelated archived plan doc. Docs re-pointed at `module-tests` in `testing-standards.md` (5 spots), `cross-skill-integration.md`, `test/pm-dev-frontend/README.md`. |
| D2 | Finding-clearing requires executed-test evidence | A build that executes no tests cannot clear a test-failure finding; the check publishes the population | Yes | Yes | **Partly — see G1** | Yes (single clearing path) | `_build_shared.py:430` `_reconcile_pending_build_findings(plan_id, command_str, tests_run)`; `:466-468` `clearable_types` excludes `test-failure` unless `tests_run > 0`; `:751` `tests_run = test_summary.total if test_summary is not None else 0`; `:776` publishes `tests_run` on the success result; `_build_format.py:49` whitelists it. `resolve_findings_by_type` has exactly one production caller (grep). Mutation `> 0` → `>= 0` turned 2 tests RED. Executed `format_toon` → `tests_run: 42` / `tests_run: 0`. **Defect:** `total` = passed+failed+skipped (`_build_parse.py:193`, `_pyproject_cmd_parse.py:539`), so a skipped-only green run reports `tests_run=5` and clears a `test-failure` finding — executed, see G1. |
| D3 | Delete dead module-stubbing mocks | No file implies an isolation it does not have | Yes | Yes | Yes | **Prose drift — see G4** | `grep -rn "sys.modules.setdefault" test/` → 0 code sites; the only hits are comments at `test/conftest.py:189` and `test/conftest.py:1153`, both of which still describe the removed pattern as present. The 7th `setdefault` (`test_get_module_context.py`) was a real-module registration and has since been reworked by a later plan (`git log` → `#1270`, `#1283`) — superseded, not a gap. |
| D4 | Normalise developer paths out of fixtures | No fixture contains a real user's home path | Yes | Yes | Yes | Yes | `grep -rn "Users/oliver" test/` → 0 files; `grep -rn "home/oliver" test/` → 0. Remaining `/Users/` hits are generic placeholders (`/Users/test/`, `/Users/dev/`), which the done-when does not forbid. |
| D5 | Scope the autouse pollution guard via a marker | It no longer runs on every test | Yes | Yes | Yes | **No — see G2** | `test/conftest.py:733-735` `pytest_collection_modifyitems` adds `touches_real_state` when `'plan_context' in item.fixturenames`; `:960-965` `_pollution_guard` returns early without the marker. Marker registered at `pyproject.toml:207`; the "complete set of custom markers" comment says six and `tomllib` confirms exactly 6. Re-derived at HEAD: 4063/20974 tests marked. **Defect:** the predicate is the `plan_context` *fixture* only; the `PlanContext`/`BuildContext` context managers and the four files that set `PLAN_BASE_DIR` by hand are unmarked. |
| D6 | Retire the manual environment save/restore | One mechanism owns those globals | Partially | Deviation declared in the report | Yes for the three classes changed | **No — see G3** | `conftest.py:1588,1603` (PlanContext), `:1988,2005` (BuildContext) and `test_manage_files.py:50,59` (EmptyPlanContext) now use a `pytest.MonkeyPatch()` reverted by `undo()`; zero call-site changes (diff confirms only the class bodies changed). But at `fa452e0c~1` six files wrote `os.environ['PLAN_BASE_DIR']` directly and only two were converted; 28 sites across 4 files survive at HEAD. |
| D7 | Falsifiability control | The control passes | Yes | Yes | Yes | Yes | `test/test_runner_falsifiability.py` — failing file → pytest non-zero + `'1 failed'`; passing file → exit 0 (matched pair, so the red is a real verdict); same failing file run as a script → exit 0 (documents the retired defect). 3 passed. The subprocess launches are genuine (timed a comparable bare launch at 0.27s vs the 0.58s total). |

**D2.** The guard is real and falsifiable, and the population is genuinely published on both the
zero and non-zero branch. The residual defect is the *definition* of the population:
`cmd_run_common` uses `test_summary.total`, and both summary producers define `total` as
`passed + failed + skipped`. A green run whose only outcome is skips therefore presents a non-zero
"executed-test count" and clears a pending `test-failure` finding although no test body ran. That
is the plan's own defect class surviving inside the fix, narrowed rather than closed
(`_build_shared.py:751`, `_build_parse.py:193`, `_pyproject_cmd_parse.py:539`).

**D5.** The scoping predicate is `'plan_context' in item.fixturenames`. `conftest.py:718-722`
states that a credential/plan test reaching real state without that fixture "opts in by carrying
the marker explicitly" — `grep -rn "mark.touches_real_state" test/` returns **0**, so no test
takes that route. Meanwhile six test files drive plan/build state through the `PlanContext` /
`BuildContext` context managers without ever mentioning `plan_context`
(`test_execute_script.py`, `test_npm_discover_modules.py`, `test_npm.py`, `test_npm_discover.py`,
`test_pyproject_build.py`, `test_gradle_discover_modules.py`), and four more override
`PLAN_BASE_DIR` by hand (below). The backstop was removed from exactly the population that
overrides the sandbox.

**D6.** The report's deviation (keep the `with X()` API, swap the mechanism) is declared and
defensible. The completeness claim is not: `git grep -c "os.environ\['PLAN_BASE_DIR'\] = "
fa452e0c~1 -- test/` lists six files; the plan's run converted two (`conftest.py`,
`test_manage_files.py`) and left four untouched — `test_maven_run.py` (2 sites),
`test_npm_run.py` (2), `test_build_parse.py` (2), `test_logging.py` (22). All four still stand at
HEAD. `test_logging.py` is the sharpest instance: 22 tests end with
`del os.environ['PLAN_BASE_DIR']`, which does not restore the autouse sandbox's value but removes
the variable outright for the remainder of the test body. Separately,
`test_list_providers.py` assigns `_config_core.PLAN_BASE_DIR` / `MARSHAL_PATH` directly at 24
sites with no restore at all (12 of them predate this plan). The done-when "one mechanism owns
those globals" is not met.

## Report accuracy

Contradictions found:

1. **Residue, first bullet — wrong placeholder for build-maven.** The report says generic
   `/Users/dev/` placeholders remain in "`test/plan-marshall/build-maven/fixtures/sample-maven-*.log`".
   `git grep -l "/Users/dev" fa452e0c -- test/plan-marshall/build-maven/` returns nothing, and at
   HEAD those files contain `/Users/test/` (7, 6, 3 and 2 occurrences in
   `sample-maven-failure.log`, `sample-maven-success.log`, `sample-maven-javadoc.log`,
   `sample-maven-openrewrite.log`). A future consistency pass following that bullet would search
   for the wrong string.
2. **Residue, first bullet — under-derived population.** `/Users/dev/` also occurs in three
   files the residue does not name: `test/plan-marshall/platform-runtime/test_pretooluse_gate.py`
   (6 occurrences), `test_claude_pretooluse_hook.py` (2), `test_claude_pretooluse_capture.py` (2).
   All three carried them at `fa452e0c` already.
3. **D6 — "one mechanism owns those globals" is overstated.** See the D6 paragraph: four files /
   28 manual `os.environ['PLAN_BASE_DIR']` writes survive at HEAD, plus 24 unrestored
   `_config_core.PLAN_BASE_DIR` assignments. The report enumerates three classes and treats that
   enumeration as the population — the same "expected surface is a lead, not a population" trap
   the report itself identifies for D4 in its own "What have we learned".
4. **Minor count drift (immaterial).** The report states "2 of 765 `test_*.py` files"; re-derived
   at `fa452e0c~1` the denominator is 769 (the numerator, 2, is confirmed). "~12 have any
   `__main__` block" re-derives to 13.

Checked and found **no** contradiction in: the D2 mechanism description (gate location, split of
clearable types, the published field and the `EXTRA_FIELDS` whitelist), the single-caller claim
for the clearing path, the D3 count of 6 removed stubs and the out-of-scope classification of the
7th, the D4 absence claim (`/Users/oliver` and `/home/oliver` → 0), the D5 marker registration and
the five→six marker-comment update, the D7 control's three cases, the "no call-site changes"
claim for D6, and the finding-2 fix (the `BUILD_FINDING_TYPES` comment at `_build_shared.py:262-266`
now states the split correctly).

## Out-of-scope compliance

Compliant. The plan bars changes to `marketplace/bundles/**` "the code under test", but its own
Expected surface lists "The finding-clearing path (D2)", which lives there. The landed diff touches
exactly four bundle files: `_build_shared.py` and `_build_format.py` (D2 mechanism + population
publishing), `build-api-reference.md` (D2 output-schema doc), and
`testing-standards.md` + `cross-skill-integration.md` (D1 doc re-pointing). No production behaviour
under test was changed to make the harness pass. No undeclared collateral change appears in the
32-file diff; every remaining path is a test file, a fixture, `pyproject.toml`, or the plan
directory itself (`plan.md` arrives by `git mv`, as the report's Step 3 claims).

## Residue carried forward

| Report residue | Status in today's tree |
|---|---|
| Generic `/Users/dev/` placeholders remain in build-gradle (mocks + fixtures) and "build-maven sample logs" | **Still open, and mis-stated.** build-gradle confirmed (`sample-gradle-failure.log`, `sample-gradle-javadoc.log`, `log-test-data/gradle-failure-real.log`, `log-test-data/gradle-test-failure-real.log`, `mocks/gradlew-failure.sh`, `mocks/gradlew-javadoc.sh`). build-maven is wrong — see Report accuracy #1. Three platform-runtime test files also carry `/Users/dev/` and are unlisted. |
| `pyproject.toml` still cites "14794 tests" in the `filterwarnings` rationale | **Still open.** `pyproject.toml:112` reads "whole-tree run of all 14794 tests"; re-derived at HEAD, collection reports **20974** tests. Correctly flagged as pre-existing drift, not introduced here. |

The report declares no deferred deliverable and no survivor finding; findings 1 and 2 are fixed
and verified fixed at HEAD, and finding 3 was correctly rejected as a read-ordering artifact.

## What could NOT be verified

- **D5's cost measurement (398.59s → 369.09s, ~7.4%).** A single before/after pair on the run's own
  cloud runner. Not reproducible here without a full-suite double run on identical hardware, and
  the guard's cost is machine- and `.plan/local/`-population dependent by its own argument. The
  plan required the number be *reported*, which it was; the number itself stands unaudited.
- **The report's D5 population figures at its own commit ("3330 tests / 189 files").** Re-derived
  at HEAD as 4063 of 20974 collected; the suite has grown since, so the figures are neither
  confirmed nor contradicted.
- **The D2 verification figure "2081 build-code tests green"** and the D3 figure "135 tests in the
  6 files" — both are point-in-time run outputs, not re-derivable from the tree at HEAD.
- **The whole-suite `./pw verify` result (19623 passed, 14 skipped in 369.09s).** Not re-run here;
  a bounded 1975-test subset covering every file the plan touched was run instead and is green.
- **The PR-surface claims** (reviewer coverage 1 of 3, rate-limit notices, auto-merge arming). The
  commit landed as `fa452e0c`, which is consistent with the merge, but the review surfaces were not
  read.
