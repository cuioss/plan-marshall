# Test Fixture & Bootstrapping Inventory

Complete inventory of every `conftest.py` and every shared-helper / fixture
module present under `test/**`, evaluated against the
`pm-dev-python:pytest-testing` fixture-discovery semantics. For each entry:
path, what it defines, its import consumers, and where two entries diverge or
duplicate the same bootstrapping logic.

Analysis-only — no test or production file is modified.

## Confirmed structural facts

- **Exactly one `conftest.py` exists: `test/conftest.py`.** A `git ls-files`
  sweep for `test/**/conftest.py` returns only the root file. There are **no
  per-bundle / per-skill `conftest.py` files**, confirming the single-root-conftest
  design.
- **`test/adapters/conftest.py` does NOT exist.** The `solution_outline.md` D2
  survey list references it, but `git ls-files 'test/adapters/*'` returns
  nothing — there is no `test/adapters/` directory. That outline reference is
  stale and is corrected here.
- **`build_test_helpers.py` and `discovery_test_helpers.py` DO exist** at
  `test/plan-marshall/`. The outline's provisional note that "the originally-named
  `build_test_helpers.py` / `discovery_test_helpers.py` do not exist under those
  names" is **incorrect** — both are present on disk and are actively imported
  shared-assertion helpers (see the inventory below). This is the single most
  important correction to the outline-time assumptions.
- **The single-root-conftest design is deliberate and enforced by convention.**
  Every sibling helper module carries a docstring explaining it is named
  `_*.py` (NOT `conftest.py`) specifically because a sub-directory `conftest.py`
  would shadow `test/conftest.py` and silently disable the shared fixtures. The
  repo's own `plugin-doctor` `unique-fixture-basenames` / `subprocess-pythonpath`
  test-convention rules enforce this.

## The bootstrapping keystone: `test/conftest.py`

`test/conftest.py` is the single bootstrap for the whole suite. It defines:

**Path constants**: `TEST_ROOT`, `PROJECT_ROOT`, `MARKETPLACE_ROOT`,
`PLAN_DIR_NAME`, `TEST_FIXTURE_BASE`.

**Collection config**: `collect_ignore[]` — excludes the four integration/real-tree
smokes (`discover_modules` integration, `module_aggregation`, the three
`tools-marketplace-inventory` real-tree smokes, and the `plugin-doctor`
manage-invocation smoke) from the default in-process module-tests run.

**Session bootstrap**:
- `_ensure_executor_present()` — generates `.plan/execute-script.py` if missing
  (CI runner cold-start), idempotent.
- `_setup_marketplace_pythonpath()` → `_MARKETPLACE_SCRIPT_DIRS` — scans every
  `marketplace/bundles/*/skills/*/scripts/` (and immediate subdirs) onto
  `sys.path`, mirroring the executor's PYTHONPATH so tests can bare-import any
  script module (`toon_parser`, `ci_base`, `extension_base`, `_config_core`,
  `_providers_core`, `plan_logging`, `run_config`, …).
- **Test-helper sys.path**: adds **only** `test/plan-marshall` and
  `test/pm-plugin-development` to `sys.path` (lines 192-198). This is the
  keystone asymmetry driving the fixture duplication documented below.

**Script-runner surface** (the primary shared test API):
- `class ScriptResult` — `.success`, `.json()`, `.toon()`, `.json_or_error()`,
  `.toon_or_error()`.
- `run_script(script_path, *args, ...)` — subprocess a script with the mirrored
  PYTHONPATH, capture output.
- `get_script_path(bundle, skill, script)`, `get_scripts_dir(bundle, skill)`,
  `load_script_module(bundle, skill, script_file, module_name=None)` — the
  centralized `importlib.util.spec_from_file_location` loader that REPLACES the
  per-test importlib boilerplate.
- `create_temp_file`, `create_temp_dir`, `load_fixture`, `assert_json_structure`.

**Autouse isolation fixtures** (the four-layer isolation contract):
- `_restore_cwd` — restores cwd after each test.
- `_plan_base_dir_sandbox` — redirects `PLAN_BASE_DIR` (env + `_config_core`
  attrs) into a per-test xdist-safe tmp sandbox; opt out with
  `@pytest.mark.allow_pollution`.
- `_credentials_dir_sandbox` — the credentials sibling (redirects
  `_providers_core.CREDENTIALS_DIR`).
- `_pollution_guard` — fails loudly if a test leaks into the real
  `~/.plan-marshall/credentials/` or the real repo-local `.plan/local/` tree
  (shallow snapshot before/after).

**Explicit fixtures / context managers**: `plan_context` (fixture),
`PlanContext`, `BuildContext` (context managers), `create_marshal_json`,
`create_raw_project_data`, and the `MARSHAL_SCHEMA_DEFAULT` schema constant.

**Consumers**: effectively every test file in the suite (via `from conftest
import run_script, get_script_path, ...` and the autouse fixtures).

## sys.path reachability map (the duplication root cause)

Whether a shared helper can be bare-imported from another bundle's test file is
governed entirely by which dirs `test/conftest.py` puts on `sys.path`:

| Helper location | Bare-importable from anywhere? | Why |
|-----------------|-------------------------------|-----|
| `test/plan-marshall/*.py` | **Yes** | `test/plan-marshall` is on sys.path |
| `test/pm-plugin-development/*.py` | **Yes** | `test/pm-plugin-development` is on sys.path |
| `test/<other-bundle>/<skill>/_*.py` | **No** | only importable as a same-directory sibling by test files in that dir (pytest prepend-import mode) |

Consequence: a helper that a `pm-dev-java` or `pm-documents` test needs but that
lives canonically under `test/plan-marshall/` **cannot be imported** — so it is
**physically duplicated** into the consuming bundle's test dir. This is the
mechanism behind the input-validation fixture triplication below.

## Shared-helper / fixture-module inventory

Every non-`__init__.py`, non-`conftest.py` helper module under `test/**`,
catalogued. "Reach" = bare-importable (on sys.path) vs sibling (same-dir import
only).

### On-sys.path shared helpers (under `test/plan-marshall/`, bare-importable)

| Module | Defines | Consumers | Reach |
|--------|---------|-----------|-------|
| `test/plan-marshall/build_test_helpers.py` | Coverage assertions (`assert_coverage_missing_file/high/low/has_low_items/custom_threshold`), execute-config assertions (`assert_execute_config`, `assert_command_key_fn`, `assert_scope_fn`), `assert_run_help` | `build-gradle`, `build-maven`, `build-npm`, `build-pyproject` coverage/execute/run tests | bare |
| `test/plan-marshall/discovery_test_helpers.py` | Module-discovery contract assertions (`assert_valid_module`, `assert_module_paths`, `assert_module_stats`, `assert_module_commands`, `assert_command_uses_executor`, `assert_canonical_commands_present`) | `build-*` `discover_modules` tests across all backends | bare |
| `test/plan-marshall/_pm_input_validation_fixtures.py` | Canonical 6-axis identifier-validation matrix (`_BASE_MALFORMED`, `REJECTION_AXES`, `MALFORMED_AXES`, `HAPPY_VALUES`), assertion helpers (`parse_toon_output`, `assert_invalid_field`, `assert_not_invalid_field`) for 13 identifier flags | every plan-marshall `manage-*` `test_*_input_validation.py` (~12 files) | bare |
| `test/plan-marshall/_resolve_project_dir_fixtures.py` | `--plan-id`/`--project-dir` two-state contract fixtures: `CANONICAL_PLAN_ID/WORKTREE/PROJECT_DIR`, `patch_query_worktree_path`, `patch_main_checkout_root`, `assert_accepts_plan_id_flag`, `assert_accepts_project_dir_flag` | 21 Bucket-B consumer test files (build-*, tools-integration-ci, extension-api, ext-self-review, workflow-integration-{github,gitlab,sonar}, workflow-pr-doctor, manage-references, manage-architecture, script-shared, execute-task) | bare |

### Skill-scoped sibling helpers (same-dir import only)

| Module | Defines | Consumers | Reach |
|--------|---------|-----------|-------|
| `test/plan-marshall/manage-architecture/_arch_fixtures.py` | `seed_project`, `setup_test_project`, `create_test_project(shape=...)`, `_default_enrichment_stub` — hoisted from per-file duplicates (outline "D5") | `manage-architecture` `test_cmd_suggest`, `test_enrich_*`, `test_cmd_client`, `test_cmd_manage` | sibling |
| `test/plan-marshall/manage-config/_layout_sim.py` | `bare`, `write_phase_standards`, `build_phase_layout` — build a fake bundle standards tree (source + versioned-cache layouts) for step-order discovery | `manage-config` step-discovery tests (`test_steps_sort`, `test_finalize_step_presets`, etc.) | sibling |
| `test/plan-marshall/manage-execution-manifest/_execution_manifest_fixtures.py` | `FakeExtension` (ExtensionBase subclass), `fake_python_extension`, `fake_documentation_extension`, `fake_plugin_dev_extension`, `fake_lane_blocks` | `manage-execution-manifest` classifier + lane tests | sibling |
| `test/plan-marshall/manage-lessons/_lessons_helpers.py` | `SCRIPT_PATH`, `_mod` + all `cmd_*` re-exports, `get_next_id`, `_FakeDatetime` freezer | the 20 split `test_manage_lessons_*.py` / per-verb files | sibling |
| `test/plan-marshall/manage-tasks/_helpers.py` | Namespace builders (`_add_ns`, `_update_ns`, `_finalize_step_ns`, …), `build_task_toon`, `add_basic_task`, `cmd_*` re-exports via `load_script_module` | the split `test_manage_tasks_*.py` files | sibling |
| `test/plan-marshall/manage-providers/_providers_fixtures.py` | `stage_marshal(base_dir, monkeypatch, config)` — isolated marshal.json staging that composes with the autouse sandbox | `manage-providers` tests | sibling |
| `test/plan-marshall/plan-doctor/_doctor_fixtures.py` | `REAL_LESSON_IDS`, `CANONICAL_PHASES`, `make_plan_with_tasks`, `seed_lesson_inventory`, `make_status_json`, `make_healthy_plan`, `make_worktree_dir`, `make_archived_plan` | `plan-doctor` `test_plan_doctor.py` | sibling |
| `test/plan-marshall/plan-marshall/_handshake_fixtures.py` | Module loaders (`_git_helpers`/`_handshake_store`/`_handshake_commands`/`_invariants` + sys.path shim), fixtures `stubbed_invariants`, `stub_metadata`, `required_steps_path`, `only_phase_steps_invariant`, `_ns` | the split `test_phase_handshake_*.py` files | sibling |
| `test/plan-marshall/plan-retrospective/_plan_retrospective_fixtures.py` | `write_handshakes`, `build_happy_plan_dir`, `build_broken_plan_dir`, `setup_live_plan`, `setup_broken_plan`, `setup_archived_plan`, `write_captured_real_log`, `_HANDSHAKE_FIELDS` (kept lock-step with production) + frozen real-log fixture | the many `plan-retrospective/test_*.py` files | sibling |
| `test/pm-plugin-development/plugin-doctor/_fixtures.py` | The firing-fixture corpus for the plugin-doctor suite-coverage meta-test: `FixtureSpec`, `build_fixture_corpus()` (one known-defect fixture per rule ID), `registered_rule_ids`, `fired_rule_ids`, `record_fired`, `crossfile_verified_findings` — loads ~55 analyzer modules via `conftest.load_script_module` | `plugin-doctor/test_zero_match_suite_coverage.py`, `test_analyze_crossfile.py` | bare (under pm-plugin-development, on sys.path) |

### Duplicated sibling copies (the divergence findings)

| Module | Defines | Duplicates |
|--------|---------|-----------|
| `test/pm-dev-java/maven-profile-management/_maven_profile_input_validation_fixtures.py` | `_BASE_MALFORMED`, `MALFORMED_AXES`, `HAPPY_VALUES` (`module` only), `parse_toon_output`, `assert_invalid_field`, `assert_not_invalid_field` | **byte-identical core** to `_pm_input_validation_fixtures.py` |
| `test/pm-documents/manage-interface/_manage_interface_input_validation_fixtures.py` | same shape (`field` only) | **byte-identical core** to `_pm_input_validation_fixtures.py` |

## Divergence & duplication findings

### D2-1 — Triplicated input-validation fixture factory (HIGH) — CONFIRMED

`_pm_input_validation_fixtures.py` (canonical, 13-field matrix),
`_maven_profile_input_validation_fixtures.py` (subset: `module`), and
`_manage_interface_input_validation_fixtures.py` (subset: `field`) share a
**byte-identical** `_BASE_MALFORMED` list (the 5 malformed axes:
`empty` / `path-separator` / `glob-meta` / `traversal` / `overlong`) and
byte-identical `parse_toon_output`, `assert_invalid_field`,
`assert_not_invalid_field` implementations. The two bundle copies are pure subset
duplicates.

**Root cause (self-documented).** Both copies' docstrings state verbatim that
they are "duplicated here (rather than imported via cross-bundle PYTHONPATH)
because pytest only adds `test/plan-marshall` and `test/pm-plugin-development`
to `sys.path` (see `test/conftest.py`)." The duplication is a **direct
consequence of the conftest sys.path asymmetry**, not an oversight. This is the
key finding the D3 unification proposal must resolve.

### D2-2 — `importlib.spec_from_file_location` boilerplate partially centralized (MEDIUM)

`test/conftest.py` now provides `load_script_module(bundle, skill, script_file)`
that replaces the per-test importlib triple (`spec_from_file_location` →
`module_from_spec` → `exec_module`). Consumers HAVE migrated in places
(`manage-tasks/_helpers.py`, `plugin-doctor/_fixtures.py` both use it), but
several helpers still **open-code the same importlib boilerplate**:
`manage-architecture/_arch_fixtures.py` (`_load_module`),
`manage-lessons/_lessons_helpers.py` (inline `spec_from_file_location`), and the
per-backend build tests (`test_gradle_run_config_key.py`, etc. — their `_load`
helper, cross-referenced in the redundancy report's Cluster A). Divergence: two
loading conventions coexist (centralized `load_script_module` vs open-coded
`_load`).

### D2-3 — Ad-hoc `sys.path.insert` shims scattered across sibling helpers (MEDIUM)

Several helpers re-implement per-module sys.path manipulation to reach script
modules the conftest PYTHONPATH does not pre-add:
`_handshake_fixtures.py` (`sys.path.insert(0, str(SCRIPTS_DIR))` for
`_git_helpers`/`_handshake_store`/`_invariants`),
`_plan_retrospective_fixtures.py` (`sys.path.insert` for the `manage-files`
`toon_parser`), and `_arch_fixtures.py` (path-walk to the manage-architecture
scripts dir). Each re-derives the marketplace scripts path independently. This
is a divergence from the conftest-owned PYTHONPATH bootstrap — the same intent
(reach a script module) solved three different ways.

### D2-4 — Two fixture-storage conventions for phase-handshake data (LOW, note)

`_handshake_fixtures.py` and `_plan_retrospective_fixtures.py` both model
phase-handshake data but at different layers: the former stubs the in-process
`INVARIANTS` table; the latter materializes `handshakes.toon` on disk and keeps
`_HANDSHAKE_FIELDS` in lock-step with production `_handshake_store.HANDSHAKE_FIELDS`.
These are not duplicates (different test seams) but both hard-code the
handshake schema independently — a drift risk if `HANDSHAKE_FIELDS` changes.

### D2-5 — Isolation fixtures correctly centralized (POSITIVE, no action)

The four autouse isolation fixtures (`_plan_base_dir_sandbox`,
`_credentials_dir_sandbox`, `_pollution_guard`, `_restore_cwd`) and the
`plan_context` / `PlanContext` / `BuildContext` contexts all live once in
`test/conftest.py` — no duplication. `_providers_fixtures.stage_marshal`
correctly *composes with* (rather than duplicates) the autouse sandbox. This is
the model the duplicated input-validation factories should follow.

## Evaluation against `pm-dev-python:pytest-testing`

- **Fixture discovery**: The single-root-conftest + explicitly-imported
  `_*.py` sibling pattern is a deliberate, correct application of pytest's
  discovery semantics (a sub-dir `conftest.py` auto-imports and would shadow the
  root). The convention is sound and enforced by the repo's own plugin-doctor
  rules (`unique-fixture-basenames`, `subprocess-pythonpath`).
- **Isolation**: the autouse `tmp_path`/`monkeypatch`-based sandbox + pollution
  guard is exemplary — it is the root-cause isolation fix the standard prescribes
  (redirect at the resolver, verify the redirect held).
- **DRY gap**: the standard's "shared setup belongs in one place" principle is
  violated only by the sys.path-forced input-validation triplication (D2-1) and
  the scattered importlib/sys.path shims (D2-2, D2-3) — all three are addressable
  without weakening isolation.

## Cross-references

- Redundancy clusters that lean on these helpers (build-backend `run_config_key`
  Cluster A, coverage Cluster D, discover-modules Cluster E): see
  `test-suite-redundancy-report.md` (D1).
- Unification design resolving D2-1 (sys.path asymmetry), D2-2 (loader
  convention), D2-3 (sys.path shims): see `test-fixture-unification-proposal.md` (D3).
- Prioritized remediation units: see `test-suite-remediation-map.md` (D4).
