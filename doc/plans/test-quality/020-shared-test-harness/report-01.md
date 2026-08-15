# Run report — 020-shared-test-harness (run 01)

**Date (UTC):** 2026-08-15    **Branch:** `claude/shared-test-harness-keyzwy`    **PR:** _pending_    **Outcome:** _pending_

## Skills loaded

Loaded by path from the bundle source (`marketplace/bundles/{bundle}/skills/{skill}/SKILL.md`) — the
`plan-marshall` plugin is not installed in this cloud session, so the `Skill:` notation route was not
attempted.

| Skill | Why |
|---|---|
| `cloud-plan-lane` (`.claude/skills/`) | The lane contract — first action of the run |
| `plan-marshall:ref-code-quality` | Always |
| `pm-plugin-development:plugin-script-architecture` | Always |
| `pm-dev-python:pytest-testing` (+ `standards/testing-pytest.md`) | The plan is entirely Python tests |

No skill was unobtainable by both routes.

## Deliverables

| # | Deliverable | Commit | State |
|---|---|---|---|
| D1 | `parse_ns` | `dc7c2c9` | Done |
| D2 | One marshal builder | `dc7c2c9` | Done |
| D3 | Retire `test_helpers.py` | `dc7c2c9` | Done |
| D4 | `test/README.md` | `2998074` | Done |
| D5 | Harness meta-tests | `2998074` | Done |
| D6 | Proof-of-use conversion | `44e56ff`, `fcde820` | Done (7 of the ≤10 ceiling) |

### D1 — `parse_ns`

`test/conftest.py` exports `parse_ns(bundle, skill, script, *argv) -> argparse.Namespace`, plus the
named error `ParserSeamNotFound` and the documented convention constant `PARSER_BUILDER_NAMES`.

**Verified:** a namespace for `manage-findings list --plan-id p1` carries `include_qgate=False` and
seven further defaults the caller never named. The no-seam path (`ci_base.py`) raises
`ParserSeamNotFound`. Both are pinned by tests in `test/test_shared_harness.py`.

### D2 — one marshal-config builder

Exactly one definition remains tree-wide (`grep -rn 'def create_marshal_json' test --include=*.py` →
1 hit, `test/conftest.py`). The two distinct baselines survive as named presets
(`MARSHAL_PRESET_MINIMAL`, `MARSHAL_PRESET_JAVA`) rather than being averaged. `create_run_config`
moved into `test/conftest.py` alongside it.

The three superseded definitions differed in three dimensions, each now an explicit argument:

| Dimension | `conftest` (old) | `test_helpers` | `test_triage_extension` | Now |
|---|---|---|---|---|
| Baseline | `MARSHAL_SCHEMA_DEFAULT` | java-flavoured | none (config required) | `preset=` / `config=` |
| Destination | `base_dir/.plan/marshal.json` | `fixture_dir/marshal.json` | `fixture_dir/marshal.json` | `nest_in_plan_dir=` |
| `raw-project-data.json` | no | **yes** | no | `with_project_data=` |

The destination difference was load-bearing, not cosmetic: `plan_context` points `MARSHAL_PATH` at
`tmp_path/'marshal.json'` directly, so a nested write lands where the script under test never looks.

### D3 — `test_helpers.py` retired

Renamed to `_manage_config_fixtures.py` (`git mv`, history preserved); all 23 importers repointed
(re-derived, matching the plan's `~23` lead exactly).

**The invariant, re-derived before and after:**

| | Collected modules scanned | Declaring zero tests |
|---|---|---|
| Before (`origin/main`) | 786 | **1** — `test/plan-marshall/manage-config/test_helpers.py` |
| After | 785 | **0** |

### D4 — `test/README.md`

Written. `test/conftest.py`'s docstring reference now resolves (it previously pointed at a file that
did not exist). Sharpened from "See test/README.md for full documentation" to name what the document
actually is, since it is navigation and ownership rather than full documentation.

### D5 — harness meta-tests

`test/test_shared_harness.py`, 20 tests, sibling of the existing `test_conftest_discipline.py`. The
whole-tree guard follows `test/marketplace/test_prefix_strip_idiom_retired.py`: population asserted
non-empty before the offender list is asserted empty.

**Falsifiability, verified by deliberately introducing each violation and observing red:**

| Property | Violation introduced | Result |
|---|---|---|
| `parse_ns` applies defaults | `parse_ns` returns a hand-built namespace | RED (3 tests) |
| `parse_ns` raises the named error | no-seam path returns `Namespace()` | RED |
| Presets stay distinct | `MARSHAL_PRESET_JAVA` → the minimal schema | RED |
| D3 invariant | added a testless `test_*.py` under `test/` | RED |

### D6 — proof-of-use conversion

Seven modules (ceiling is ten) across **five** subtrees (floor is four).

| Module | Before | After | Delta |
|---|---:|---:|---:|
| `plan-marshall/workflow-integration-git/test_worktree_move_lifecycle.py` | 309 | 288 | −21 |
| `plan-marshall/build-pyproject/test_pyproject_extension.py` | 637 | 613 | −24 |
| `plan-marshall/manage-config/test_build_decision.py` | 509 | 511 | +2 |
| `plan-marshall/manage-config/test_cache_retention_knobs.py` | 313 | 317 | +4 |
| `plan-marshall/manage-config/test_cmd_domain_detect.py` | 481 | 470 | −11 |
| `plan-marshall/manage-architecture/test_find_confident_negative.py` | 275 | 294 | +19 |
| `pm-plugin-development/plan-marshall-plugin/test_markdown_derivation_resolver.py` | 414 | 408 | −6 |
| **Total** | **2938** | **2901** | **−37** |

Three modules grew. A `parse_ns` factory carrying a docstring costs more than the `Namespace`
literals it replaces when the call count is low; reduction is plans `030`–`080`'s job, and this
deliverable buys evidence that the harness serves the shapes the tree has.

**The three required shapes are covered:**

* **Deep subparser graph** — `test_cache_retention_knobs.py` drives the three-level
  `system → retention → set` tree; `test_build_decision.py` drives the 26-verb `noun` graph.
* **Non-default marshal config** — `test_cmd_domain_detect.py` stages custom config dicts through the
  D2 builder.
* **Multi-module `_load_module` preamble** — `test_worktree_move_lifecycle.py` opened with four raw
  `spec_from_file_location` blocks; `test_build_decision.py` and `test_cache_retention_knobs.py` each
  carried a private `_load_module` plus a `Path(__file__).parent.parent.parent.parent` chain.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **32 files**. Python changed, so the gate ran.

`./pw verify` — **SUCCESS**, all three sub-steps green (quality-gate, test-compile, module-tests):
`20065 passed, 14 skipped in 345.83s`.

`test-compile` caught six `no-any-return` errors the quality gate does not run (fixed in `fcde820`).
The per-commit `./pw quality-gate` ran clean before each `*.py` commit.

### Collected-item count (the plan's load-bearing check)

| | Count |
|---|---:|
| Before, whole `test/` tree | **20059** |
| After, whole `test/` tree | 20079 |
| After, excluding the new `test/test_shared_harness.py` | **20059** |

Equal once D5's own 20 new tests are excluded, so **no module was dropped from collection** — which is
the failure this check exists to catch.

## Findings

> **This section is INCOMPLETE — the run is still in progress.** The pre-PR
> verification sub-agent (§ Step 6) has not yet reported, and the PR has not been
> opened. An empty findings list here means *not yet collected*, **not** *none
> found*. The sections below are placeholders for the same reason.

### Findings already recorded (self-caught, before the sub-agent reported)

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | Self, during D5 | `test_a_written_fixture_cannot_mutate_the_shared_baseline` claimed to guard the shallow-copy defect but **passed with the shallow copy reinstated** — the defect is unobservable through the builder's public API, which only assigns at the top level. | **Fixed** — replaced with `test_building_a_fixture_leaves_the_shared_baseline_untouched`, whose docstring states it is a forward-looking pin rather than a detector. Shipping the original would have been a vacuous green. |
| 2 | Self, during D1 | An invalid `argv` on the interception seam raised `ParserSeamNotFound`, conflating "your command line is wrong" with "this script has no seam" — and differing from the builder seam, which raises `SystemExit` for the same mistake. | **Fixed** — the interception path tracks whether the real parser was entered and re-raises `SystemExit` when it was, so both seams fail identically. |
| 3 | `./pw verify` (`test-compile`) | Six `no-any-return` errors: `conftest` is deliberately opaque to mypy (`ignore_missing_imports`), so `parse_ns(...)` reads as `Any` and every factory annotated `-> Namespace` tripped `warn_return_any`. Not caught by `./pw quality-gate`, which does not run mypy over `test/`. | **Fixed** in `fcde820` — bound through a declared local rather than six `type: ignore` comments. |
| 4 | Self, during D6 | `conftest.load_script_module` resolves only `{bundle}/skills/{skill}/scripts/{file}`, so a domain bundle's **skill-root** `extension.py` (10 such files) cannot use it. | **Recorded as a proposal, not fixed** — widening the loader is outside D1/D2, the plan's declared `conftest.py` surface. The module uses `MARKETPLACE_ROOT` to kill the `Path(__file__).parent…` chain and keeps an explicit spec load. |
| 5 | Self, during D6 | `test_cmd_domain_detect`'s dispatch-registration test built its **own** stand-in parser, registered the subcommand on it, and asserted the routing it had just configured — proving only that argparse works, not that manage-config registers the verb. | **Fixed** — routed through the real parser via `parse_ns`. |
| 6 | D4 reading test (§ Verification) | The three-subtree row offered "`test/conftest.py` or `test/_shared/`" with no rule for choosing, and said to record a proposal without naming a channel — while the two-subtree row directly above it does name one. | **Fixed** — both stated in `test/README.md`. |

## Reviewer participation

_Pending — the PR has not been opened._

## Cost

_Pending._

## Contract check (Step 9)

_Pending._

## What have we learned (Step 9)

_Pending._

## Residue

_Pending._
