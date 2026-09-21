# Gaps — 380-test-suite-false-confidence

**Source:** verification.md (same directory)   **Open items:** 8

## G1 — Count only executed tests in `tests_run`, not skipped ones

- **Kind:** bug
- **Severity:** high
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py:751` — `cmd_run_common`; the gate it feeds is `_build_shared.py:467`; the population it reads is declared at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_parse.py:191-194` (`UnitTestSummary`) and produced by **five** parsers, every one of which folds skips into `total`: `_pyproject_cmd_parse.py:535-540`, `_build_parse.py:610-624`, `_maven_cmd_parse.py:164-176`, `_npm_parse_jest.py:156-166`, `_npm_parse_tap.py:160-174`.
- **What is wrong:** D2 gates the clearing of a `test-failure` finding on `tests_run > 0`, described throughout as "the executed-test count" (`_build_shared.py:448`, `_build_format.py:74-78`, `build-api-reference.md:90-94`). `tests_run` is `test_summary.total`, and every producer defines `total` as `passed + failed + skipped` (maven and jest take `total` straight from a tool figure — surefire's `Tests run:` and jest's `N total` — both of which include skips).
  Executed end-to-end at HEAD, with `resolve_findings_by_type` replaced by a capture stub:
  `_extract_pytest_summary('===== 5 skipped in 0.42s =====')` → `UnitTestSummary(passed=0, failed=0, skipped=5, total=5)`; feeding `total` into `_reconcile_pending_build_findings('some-plan', 'module-tests', 5)` yields `finding_types=('build-error', 'lint-issue', 'test-failure')` and `detail='auto-resolved by green build (5 test(s) executed): module-tests'`. The `test-failure` type is cleared and the published detail asserts five executions that never happened.
- **Why it matters:** a green build that executed nothing but skips destroys a true, already-recorded `test-failure` finding — the exact mechanism D2 exists to stop, narrowed rather than closed. Two distinct failure modes, both live:
  1. **skips-only** — the finding is cleared with no test body having run;
  2. **mixed run** — `tests_run` overstates the executed population by exactly the skip count, so the field D2 exists to *publish* is wrong even when the clearing decision happens to be right.
  Reachability is concrete, not hypothetical: `test/sync-plugin-cache/test_sync_engine.py` collects 11 tests of which 9 are `skipif(shutil.which('rsync') is None)`-guarded, and `test_staleness_guard.py` is guarded the same way on `git`/`rsync`; a scoped `module-tests` run over that directory on a host lacking those binaries produces a skip-dominated (or skips-only, under any `-k` narrowing) summary. Nothing else catches it — the suite's zero-skip gate is inert (see G8).
- **Fix:** in `cmd_run_common` (`_build_shared.py:751`), compute `tests_run = test_summary.passed + test_summary.failed` — or add an `executed` property to `UnitTestSummary` in `_build_parse.py` and use it — leaving the published `tests_run` field defined as *executed*. Update the three places that state the definition to match: the `_reconcile_pending_build_findings` docstring (`_build_shared.py:445-457`), the `tests_run` paragraph of the `EXTRA_FIELDS` docstring (`_build_format.py:74-78`), and `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-api-reference.md:87-94`. Add a test in `test/plan-marshall/build-pyproject/test_build_findings_store.py` driving `cmd_run_common` with a parser returning `UnitTestSummary(passed=0, failed=0, skipped=5, total=5)` and asserting the seeded `test-failure` finding survives, plus a mixed case (`passed=2, skipped=9, total=11`) asserting the published `tests_run` is 2.
- **Done when:** a green build whose summary is skips-only leaves a pending `test-failure` finding pending and publishes `tests_run: 0`; and a green build reporting `2 passed, 9 skipped` publishes `tests_run: 2`.
- **Module/topic:** `plan-marshall:script-shared` build finding reconciliation (D2).

## G2 — Extend the `touches_real_state` predicate beyond the `plan_context` fixture

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `test/conftest.py:733-735` — `pytest_collection_modifyitems`
- **What is wrong:** the marker is applied only when `'plan_context' in item.fixturenames`. `test/conftest.py:719-721` states the design's other half — a state-driving test without that fixture "opts in by carrying the marker explicitly" — but `grep -rn "mark.touches_real_state" test/` returns **0**: that half has no users at all, so the guard's real scope is the fixture, not the property the docstring names. Six files drive plan/build state through the `PlanContext` / `BuildContext` context managers with no mention of `plan_context` (`test/plan-marshall/tools-script-executor/test_execute_script.py` 1 site, `test/plan-marshall/build-npm/test_npm_discover_modules.py` 19, `test/plan-marshall/build-npm/test_npm.py` 3, `test/plan-marshall/build-npm/test_npm_discover.py` 16, `test/plan-marshall/build-pyproject/test_pyproject_build.py` 9, `test/plan-marshall/build-gradle/test_gradle_discover_modules.py` 14 — re-derived at HEAD by `comm`-ing the two grep sets), and four more override `PLAN_BASE_DIR` by hand (see G3). None of them is marked, so `_pollution_guard` (`test/conftest.py:960`) skips its before/after snapshot for all of them.
- **Why it matters:** the guard is now scoped by a *proxy* for the property it claims to check, and the documented escape valve that was supposed to cover the proxy's misses is unused. Those files are precisely the ones that override the autouse sandbox rather than relying on it — `PlanContext` re-points `PLAN_BASE_DIR` at `.plan/temp/test-fixture/standalone-*` (`test/conftest.py:1507-1528`, `1588-1595`), a repo-internal path — so if one of them ever resolved the real base dir instead, the backstop that exists to notice would not run. (Note the bound: that redirect is *not itself* a leak, and `.plan/temp/` is not among the watched paths — the exposure is the missing backstop, not an observed leak.)
- **Fix:** broaden the predicate in `pytest_collection_modifyitems` so a test is marked when it requests `plan_context` **or** its module references `PlanContext` / `BuildContext` / `EmptyPlanContext` / assigns `PLAN_BASE_DIR`; alternatively add `pytestmark = pytest.mark.touches_real_state` to the six files named above and the four in G3. Either way, delete or honour the "opts in by carrying the marker explicitly" sentence at `test/conftest.py:719-721` so the docstring matches the code. Add a collection-time test asserting each of the named files yields marked items.
- **Done when:** every test that enters `PlanContext`/`BuildContext` or assigns `PLAN_BASE_DIR` itself collects with `touches_real_state` (checked by `pytest --collect-only -m touches_real_state` over those ten files returning their full collected count), and the conftest docstring names only mechanisms that have users.
- **Module/topic:** `test/conftest.py` — pollution-guard scoping (D5).

## G3 — Finish retiring the manual `PLAN_BASE_DIR` save/restore

- **Kind:** incomplete-sweep
- **Severity:** low
- **Where:** `test/plan-marshall/manage-logging/test_logging.py` (22 sites, e.g. `:175`/`:180`), `test/plan-marshall/build-maven/test_maven_run.py:48-56` — `mock_maven_project`, `test/plan-marshall/build-npm/test_npm_run.py:39-47`, `test/plan-marshall/script-shared/test_build_parse.py:148-159` — `_plan_base_dir`; plus `test/plan-marshall/manage-providers/test_list_providers.py` (24 raw `_config_core` attribute assignments, e.g. `:415-416`).
- **What is wrong:** D6's stated action is "migrate remaining users to the fixture and delete the manual path", and its done-when is "one mechanism owns those globals". At `fa452e0c~1`, `git grep -c "os.environ['PLAN_BASE_DIR'] = " -- test/` listed six files; the run converted two (`conftest.py`, `test_manage_files.py`) and left four. All four still hand-roll the mutation at HEAD (28 sites total, re-derived). `test_list_providers.py` additionally assigns `_config_core.PLAN_BASE_DIR` (12 sites) and `_config_core.MARSHAL_PATH` (12 sites) raw, inside tests that already request `monkeypatch` — all 24 predate this plan (`git grep -c` at `fa452e0c~1` = 24; the file's only later commit, `8872700b` / #1263, touched no `_config_core.` line).
- **Why it matters:** the plan's own framing for D6 was "two overlapping mechanisms on one set of globals". That condition is unchanged for these five files, so the deliverable's done-when is objectively unmet and the next reader cannot tell from the code which mechanism is authoritative. The impact is confined to that: **it is not a leak.** Three of the four `os.environ` sites implement a correct `previous = os.environ.get(...)` / `finally`-restore pair, and the 22 `del os.environ['PLAN_BASE_DIR']` statements in `test_logging.py` are each the last statement of a `try/finally` — nothing in those test bodies runs after them. Across tests, the autouse `_plan_base_dir_sandbox` (`test/conftest.py:1036-1048`) applies both the env var and the `_config_core` attributes through `monkeypatch`, whose `undo()` restores the values captured *before* the test ran; it therefore repairs the raw assignments at teardown regardless of what the body did.
- **Fix:** replace each manual save/restore with the `monkeypatch` fixture (or a `pytest.MonkeyPatch()` instance reverted by `undo()`), matching `PlanContext`/`BuildContext`; in `test_list_providers.py` replace the raw `_config_core.PLAN_BASE_DIR = …` / `MARSHAL_PATH = …` assignments with `monkeypatch.setattr` (the fixture is already requested by every one of those tests). Then add a `plugin-doctor test-conventions` rule (or a guard test) rejecting `os.environ['PLAN_BASE_DIR'] =`, `del os.environ['PLAN_BASE_DIR']` and `_config_core.PLAN_BASE_DIR =` under `test/`.
- **Done when:** a tree-wide grep for direct `os.environ['PLAN_BASE_DIR'] =` / `del os.environ['PLAN_BASE_DIR']` / `_config_core.PLAN_BASE_DIR =` / `_config_core.MARSHAL_PATH =` under `test/` returns zero, and the suite is still green.
- **Module/topic:** test harness — environment sandbox ownership (D6).

## G4 — Remove the two conftest comments that still describe the deleted module stubs

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `test/conftest.py:188-190` (the pre-import rationale) and `test/conftest.py:1152-1154` (inside `_neutralize_daemon_routing`'s namespace helper)
- **What is wrong:** both comments describe `sys.modules.setdefault('plan_logging', MagicMock(...))` as a pattern test modules currently use — line 1153 says "the `MagicMock` module stand-ins several test modules install via `sys.modules.setdefault`". D3 deleted every one of them: `grep -rn "sys.modules.setdefault" test/` now returns exactly these two comment lines (189 and 1153) and no code site. Swept more broadly at HEAD: there is no `sys.modules[…] = MagicMock`/`Mock` assignment anywhere under `test/`; the 15 remaining `sys.modules` registrations all bind a real `types.ModuleType` loaded from source.
- **Why it matters:** a reader looking for the stubs to understand or extend the isolation machinery finds nothing, and may re-introduce the pattern believing it is sanctioned — the same "a claim the code does not honour" defect D3 removed.
- **Fix:** rewrite `:188-190` to state the pre-import as a defensive ordering guarantee without asserting current stub usage, and rewrite `:1152-1154` to justify the `isinstance` check on its own terms (it filters non-dict namespaces) rather than by reference to stand-ins that no longer exist.
- **Done when:** `grep -rn "sys.modules.setdefault" test/` returns zero, and no comment under `test/` asserts that test modules install `MagicMock` stand-ins.
- **Module/topic:** `test/conftest.py` — module-stub removal follow-through (D3).

## G5 — Unify the fixture placeholder root, and stop citing the wrong string for build-maven

- **Kind:** doc-drift
- **Severity:** low
- **Where:** the tree: `test/plan-marshall/build-gradle/` (`fixtures/sample-gradle-failure.log` 3, `fixtures/sample-gradle-javadoc.log` 3, `fixtures/log-test-data/gradle-failure-real.log` 3, `fixtures/log-test-data/gradle-test-failure-real.log` 1, `mocks/gradlew-javadoc.sh` 2, `mocks/gradlew-failure.sh` 1), `test/plan-marshall/platform-runtime/test_pretooluse_gate.py` (6), `test_claude_pretooluse_hook.py` (2), `test_claude_pretooluse_capture.py` (2) — all `/Users/dev`; and `test/plan-marshall/build-maven/fixtures/sample-maven-{failure,success,javadoc,openrewrite}.log` (7, 6, 3, 2) — `/Users/test`. Handover text: `report-01.md` § Residue, first bullet.
- **What is wrong:** the residue bullet says generic `/Users/dev/` placeholders remain in `test/plan-marshall/build-maven/fixtures/sample-maven-*.log`. Those files contain `/Users/test/`, not `/Users/dev/` — `git grep -l "/Users/dev" fa452e0c -- test/plan-marshall/build-maven/` matches nothing, and re-derived at HEAD the only `/Users/dev` bearers are the six build-gradle files and three `platform-runtime` test files the bullet does not name. Three placeholder roots are in play across the test tree (`/home/dev` 36 occurrences, `/Users/dev` 23, `/Users/test` 21); D4 normalised only its named surface onto `/home/dev`.
- **Why it matters:** the bullet is the handover for a future consistency pass; following it verbatim searches for the wrong string in build-maven and misses three files entirely. Independently of the bullet, the tree carries three placeholder roots where the D4 commit declared one.
- **Fix:** normalise every remaining `/Users/dev` and `/Users/test` occurrence under `test/` onto the `/home/dev` root D4 chose, in the nine `/Users/dev` files and the four build-maven sample logs listed above; re-run the owning test directories (`build-gradle`, `build-maven`, `platform-runtime`) to confirm no assertion depends on the strings. Do **not** retro-edit `report-01.md` — a run report is a dated record of one execution, not documentation of current state; this gap entry is the correction of record.
- **Done when:** `grep -rnoE "/Users/[a-z0-9_.-]+" test/` returns zero, and `grep -rnoE "/home/[a-z0-9_.-]+" test/` returns only `/home/dev` (plus the unrelated `/home/u` HOME-whitelist literal in `test/plan-marshall/build-server/test_marshalld_supervisor.py:91-95`).
- **Module/topic:** test fixtures — placeholder-path normalisation (D4 follow-on).

## G6 — Refresh the stale test count in the `filterwarnings` rationale

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `pyproject.toml:112`
- **What is wrong:** the comment reads "whole-tree run of all 14794 tests under the flags above emits ZERO warnings". Re-derived independently at HEAD (`pytest --collect-only -q -o addopts=""`): **20974** tests collected.
- **Why it matters:** the zero-warnings claim is anchored to a population that no longer exists, so a reader cannot tell whether the claim was ever re-checked against the current suite.
- **Fix:** re-run the whole-tree suite under those flags, confirm zero warnings, and replace the number with the freshly derived count — or drop the number and state the property without a population figure.
- **Done when:** the comment either names a count that matches a re-derivation at the time of the edit, or states the zero-warnings property without a count.
- **Module/topic:** `pyproject.toml` — pytest configuration comments.

## G7 — The `parse` verb publishes `metrics.tests_run` under the same name and a different definition

- **Kind:** bug
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py:185` — `cmd_parse_common`
- **What is wrong:** D2 gave the field name `tests_run` an explicit published contract — "the number of tests this run executed" (`build-api-reference.md:90-94`), and `_build_format.py:74-78` calls it "the executed-test count". `cmd_parse_common` emits a *second* `tests_run`, in `metrics`, computed as `test_summary.total if test_summary else 0` — the skipped-inclusive figure. A `parse` over a log whose summary is `5 skipped` therefore reports `metrics.tests_run: 5`. This site predates the plan (`git log -S` → `87c677bb`, #823), but the plan is what made the name a documented contract, so the two emission sites now disagree about what a published field means.
- **Why it matters:** a consumer that reads `tests_run` from either verb and treats it as executions — which the reference document instructs it to — gets a number inflated by the skip count from `parse` and (until G1 is fixed) from `run` as well. It is a distinct instance from G1: a different function, a different result envelope, and one that survives G1's fix unless changed with it.
- **Fix:** change `_build_shared.py:185` to `test_summary.passed + test_summary.failed` (or the `UnitTestSummary.executed` property added for G1) so both verbs publish the same quantity, and extend the parse-path assertions in `test/plan-marshall/build-maven/test_maven_cmd_parse.py` and `test/plan-marshall/build-operations/test_truthful_status_guard.py` (the two suites that drive `cmd_parse_common`) with a skips-only log fixture asserting `metrics.tests_run == 0` and `metrics.tests_failed == 0`.
- **Done when:** a `parse` over a log whose only test outcome is skips reports `metrics.tests_run: 0`, and the `run` and `parse` verbs return the same `tests_run` for the same log.
- **Module/topic:** `plan-marshall:script-shared` build output contract (D2 follow-on).

## G8 — The zero-skip gate is armed nowhere, while the conftest states CI arms it

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `test/conftest.py:738-741` (the flag and its rationale comment) and `test/conftest.py:756-789` — `pytest_sessionfinish`
- **What is wrong:** the comment above `_STRICT_NO_SKIP_ENV` says "the gate is off by default … CI on the reference platform sets it to `1`". Swept at HEAD across every text file in the repository outside `.git`/`.venv`: `PLAN_MARSHALL_STRICT_NO_SKIP` occurs on exactly three lines, all inside `test/conftest.py` (741, 769, 784). No workflow under `.github/`, no `pyproject.toml` entry, no `./pw` / pyprojectx target and no build script sets it, so `pytest_sessionfinish` returns at its first line on every run the project performs. The plan's own build gate corroborates it: the whole-suite run reported "19623 passed, **14 skipped**" and was green.
- **Why it matters:** this is the epic's thesis in a second place inside the safety net. A gate whose stated purpose is "a green suite that quietly covered less than it claims … the run fails rather than reporting" has never fired and cannot fire as configured, while its comment asserts that CI arms it — a guard that cannot fail, documented as armed. It also removes the one mechanism that would otherwise bound G1: a skip-dominated run is invisible to the suite as well as to the finding-clearing path.
- **Fix:** either arm it — set `PLAN_MARSHALL_STRICT_NO_SKIP: '1'` on the whole-suite job in `.github/workflows/python-verify.yml` (and reconcile the 14 skips the suite currently reports, which the gate will fail on) — or delete the gate and its flag outright and remove the "CI on the reference platform sets it to `1`" sentence. Do not leave the third state.
- **Done when:** either a grep for `PLAN_MARSHALL_STRICT_NO_SKIP` finds a producer outside `test/conftest.py` and a deliberately-skipped test makes the whole-suite job red, or `pytest_sessionfinish`'s skip gate and `_STRICT_NO_SKIP_ENV` are gone from `test/conftest.py`.
- **Module/topic:** `test/conftest.py` — suite-level coverage gate (adjacent to D7's falsifiability theme; pre-existing, introduced by #977).

## Refuted during adversarial review

Nothing in G1–G6 was refuted outright. Two clauses inside them were, and are recorded here because the
evidence is worth keeping:

- **G3, "24 sites with no restore at all" (and verification.md's D6 paragraph, same phrase).** *Refuted.*
  The autouse `_plan_base_dir_sandbox` fixture applies `monkeypatch.setattr(_config_core, 'PLAN_BASE_DIR', …)`
  and `…, 'MARSHAL_PATH', …` at `test/conftest.py:1046-1047`. `MonkeyPatch.undo()` restores the value
  captured at `setattr` time — the module's pre-test value — so a raw `_config_core.PLAN_BASE_DIR = tmp_path`
  inside the body is reverted at teardown by the sandbox's own undo. The same holds for
  `os.environ['PLAN_BASE_DIR']`, applied at `:1036` via `monkeypatch.setenv`. There is no cross-test leak;
  the surviving defect is ownership, not restoration, and G3 is re-severitied `medium` → `low` accordingly.
- **G3, "`del os.environ['PLAN_BASE_DIR']` … so anything later in that test body resolves the real
  repository tree".** *Refuted.* In all 22 `test_logging.py` occurrences the `del` is the sole statement of
  a `finally:` block and therefore the last statement executed in the test (e.g. `:175-180`). There is no
  "later in that test body". The three other files (`test_maven_run.py:48-56`, `test_npm_run.py:39-47`,
  `test_build_parse.py:148-159`) do not `del` at all — each saves `previous = os.environ.get('PLAN_BASE_DIR')`
  and restores it in `finally`.
- **G2, "the population where a real-tree leak is actually possible".** *Narrowed, not refuted.* The six
  `PlanContext`/`BuildContext` files redirect `PLAN_BASE_DIR` into `.plan/temp/test-fixture/standalone-*`
  (`test/conftest.py:1507-1528`), which is neither the real `.plan/local/` tree nor the real credentials
  directory — the two paths `_pollution_guard` snapshots (`test/conftest.py:864`, `_REAL_CREDENTIALS_DIR`).
  A leak from those tests is no *more* likely than from any other test; the defect is that the guard's
  scope is a proxy and its documented explicit-opt-in fallback has zero users. G2 stays `medium` on that
  basis, with the rationale rewritten.
