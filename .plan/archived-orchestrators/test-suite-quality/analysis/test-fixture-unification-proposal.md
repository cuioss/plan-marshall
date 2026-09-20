# Shared Bootstrapping & Fixture Unification Proposal

Design-only proposal (no implementation, no source mutation) for unifying the
shared bootstrapping and fixtures spanning all bundles, built on the D2 inventory
(`test-fixture-bootstrapping-inventory.md`). Evaluated against
`pm-dev-python:pytest-testing` fixture-discovery semantics.

The proposal presents: (1) a justified root-vs-package-scoped decision, (2) a
concrete merge map for the duplicate helper modules, and (3) per-consumer
migration notes. Nothing here is applied — this is the remediation *design*.

## Governing constraint (hard rule)

The only permitted `conftest.py` paths in this repo are `test/conftest.py` and
`test/adapters/conftest.py`. **`test/adapters/` does not currently exist**
(confirmed in D2), so in practice the single live conftest is `test/conftest.py`.
Any new package-scoped shared helper MUST be named `_*_fixtures.py` /
`_*_helpers.py` and imported explicitly — **never** introduced as a sub-directory
`conftest.py` (which would auto-import and shadow the root, silently disabling
the autouse isolation fixtures). This constraint is non-negotiable and frames
every option below.

## Decision 1 — Root conftest vs package-scoped conftest

**Decision: KEEP the single root `test/conftest.py`. Do NOT introduce any
package-scoped `conftest.py`.** Reasons:

1. **The hard rule forbids it.** Package `conftest.py` files are prohibited
   outside the two allowlisted paths, and the repo's own plugin-doctor
   test-convention rules enforce the ban.
2. **The autouse isolation contract depends on a single collection root.** The
   four autouse fixtures (`_plan_base_dir_sandbox`, `_credentials_dir_sandbox`,
   `_pollution_guard`, `_restore_cwd`) MUST apply uniformly to every test. A
   package `conftest.py` that shadowed the root would silently drop them for that
   subtree — a correctness hazard, not just a style one.
3. **Isolation is already correctly centralized (D2-5).** There is no
   duplication problem at the conftest layer — the problem is entirely in the
   `_*.py` sibling-helper layer. Splitting the conftest would solve nothing and
   create risk.

**Corollary decision — introduce ONE new on-sys.path shared-helper home.** The
root cause of the fixture duplication (D2-1) is the conftest sys.path asymmetry:
only `test/plan-marshall` and `test/pm-plugin-development` are on `sys.path`, so
cross-bundle helpers cannot be bare-imported from other bundles' test dirs. The
minimal, hard-rule-compliant fix is to add **one** neutral shared-helper
directory to the conftest sys.path bootstrap:

```text
test/_shared/            # NEW — added to sys.path by test/conftest.py
    _input_validation_fixtures.py
    (future cross-bundle helpers)
```

`test/_shared/` is a plain directory of `_*.py` modules (NOT a `conftest.py`),
appended to `sys.path` alongside the existing two entries in
`_setup_marketplace_pythonpath`'s tail. This makes cross-bundle helpers
bare-importable from every bundle's test dir without violating the conftest ban.
It is the smallest change that removes the *forced* duplication.

## Decision 2 — Merge map

| # | Source (duplicate / scattered) | Target | Action |
|---|--------------------------------|--------|--------|
| M1 | `test/plan-marshall/_pm_input_validation_fixtures.py` + `test/pm-dev-java/maven-profile-management/_maven_profile_input_validation_fixtures.py` + `test/pm-documents/manage-interface/_manage_interface_input_validation_fixtures.py` | `test/_shared/_input_validation_fixtures.py` | MERGE the canonical 13-field matrix into the shared home; DELETE the two byte-identical bundle subset copies |
| M2 | Open-coded `importlib.spec_from_file_location` `_load` helpers in `_arch_fixtures.py`, `_lessons_helpers.py`, and the per-backend build `test_*_run_config_key.py` / `test_*_execute.py` files | existing `conftest.load_script_module()` | MIGRATE call sites to the centralized loader; delete the open-coded `_load` |
| M3 | Scattered `sys.path.insert` shims in `_handshake_fixtures.py`, `_plan_retrospective_fixtures.py`, `_arch_fixtures.py` | a conftest helper `add_skill_scripts_to_path(bundle, skill)` (NEW, thin) OR reuse `load_script_module` | CENTRALIZE the "reach a script module" shim so each helper stops re-deriving the marketplace scripts path |
| M4 | Duplicated coverage fixtures (`{high,low}-coverage.xml` across build-gradle/maven/pyproject/pm-dev-java) — cross-ref D1 Cluster D | `test/plan-marshall/script-shared/fixtures/coverage/` (shared, on sys.path parent) | DEDUPE the JaCoCo fixtures into one canonical location; back-reference from each backend test |
| M5 | Byte-identical build `run_config_key` / coverage wrapper functions — cross-ref D1 Clusters A/D | extend `test/plan-marshall/build_test_helpers.py` with `assert_run_config_key_contract(...)` | EXTRACT the shared wrapper into the existing build helper (already on sys.path) |

M1 is the headline merge (it removes the only *forced* duplication). M2/M3 are
convention-unification (two loading conventions → one). M4/M5 overlap with the
D1 redundancy remediation and should be sequenced with it.

**M4 scope (JaCoCo XML subset of Cluster D — explicit).** M4 intentionally
scopes to the JaCoCo `{high,low}-coverage.xml` fixture shape shared by the four
build backends' JaCoCo parser (build-gradle / build-maven / build-pyproject /
pm-dev-java). The remaining Cluster D duplicated-fixture members are **out of
scope for M4** and require their own remediation units because their formats
differ from JaCoCo XML and are not reducible to the same shared-fixture dedup:
`build-npm`'s lcov/json coverage fixtures, `extension-api`'s Cobertura/jest
fixtures, and `pm-dev-frontend-cui`'s lcov/json fixtures.

### Shape of the merged `test/_shared/_input_validation_fixtures.py`

The canonical module already contains the full 13-field matrix and the three
assertion helpers. The merge is a **move + rename** (drop the `_pm_` prefix; the
`_shared/` location makes the prefix redundant) plus deletion of the two subset
copies. No behavior changes — the maven copy used only `module`, the interface
copy only `field`, both of which are already keys in the canonical
`HAPPY_VALUES` table (the module's public export; `_HAPPY` is its private
backing dict). The canonical module's `_malformed_for` already returns the shared
`_BASE_MALFORMED` for every field, so the subset consumers get identical values.

## Decision 3 — Per-consumer migration notes

### M1 consumers (input-validation)

- **plan-marshall `manage-*` `test_*_input_validation.py` (~12 files)**: change
  `from _pm_input_validation_fixtures import (...)` →
  `from _input_validation_fixtures import (...)`. No test-body changes — the
  symbol names (`MALFORMED_AXES`, `HAPPY_VALUES`, `assert_invalid_field`) are
  preserved. Import resolves because `test/_shared/` is now on sys.path.
- **`test/pm-dev-java/maven-profile-management/test_profiles_input_validation.py`**:
  change `from _maven_profile_input_validation_fixtures import (...)` →
  `from _input_validation_fixtures import (...)`; then delete
  `_maven_profile_input_validation_fixtures.py`. The test used only
  `MALFORMED_AXES['module']` / `HAPPY_VALUES['module']` — both present in the
  canonical matrix.
- **`test/pm-documents/manage-interface/test_manage_interface_input_validation.py`**:
  change `from _manage_interface_input_validation_fixtures import (...)` →
  `from _input_validation_fixtures import (...)`; then delete
  `_manage_interface_input_validation_fixtures.py`. Used only `field`.
- **Verification after migration**: the deleted copies leave zero importers
  (grep for the old module names must return empty); the plugin-doctor
  `unique-fixture-basenames` rule stays green because `test/_shared/` holds one
  canonically-named module.

### M2 consumers (importlib loader)

- **`_arch_fixtures.py`**: replace the local `_load_module(name, filename)` +
  `_SCRIPTS_DIR` path-walk with `load_script_module('plan-marshall',
  'manage-architecture', '_architecture_core.py')`. One-line-per-module change;
  the returned module object is drop-in.
- **`_lessons_helpers.py`**: replace the inline `spec_from_file_location` block
  with `load_script_module('plan-marshall', 'manage-lessons', 'manage-lessons.py',
  'manage_lessons')`; keep the `cmd_*` re-export lines unchanged.
- **build `test_*_run_config_key.py` (4 files)**: fold into M5 — the `_load`
  helper disappears when the shared `assert_run_config_key_contract` helper (in
  `build_test_helpers.py`) owns the `_CONFIG` resolution.

### M3 consumers (sys.path shims)

- **`_handshake_fixtures.py`**: replace the `sys.path.insert(0, str(SCRIPTS_DIR))`
  + bare imports with `load_script_module('plan-marshall', 'plan-marshall',
  '_git_helpers.py')` (etc.) OR, if the modules must be importable by their bare
  names for intra-module references, call the new
  `add_skill_scripts_to_path('plan-marshall', 'plan-marshall')` helper once.
  Choose per the module's intra-package import needs.
- **`_plan_retrospective_fixtures.py`**: the `toon_parser` sys.path shim is
  redundant — `toon_parser` is already on the conftest PYTHONPATH
  (`_MARKETPLACE_SCRIPT_DIRS` includes every `scripts/` dir). Delete the shim;
  `from toon_parser import serialize_toon` resolves via conftest.

### M4/M5 consumers (build fixtures + wrappers)

- Sequence with the D1 Cluster A/D remediation (they touch the same files).
  Migrate each backend's `test_*_coverage_report.py` to reference the shared
  `script-shared/fixtures/coverage/` dir, and each `test_*_run_config_key.py` to
  call `assert_run_config_key_contract(SCRIPT_PATH, build_tool, canonical_args)`.
  Per-backend `_CONFIG`/`CANONICAL_ARGS` stay local (they are genuinely
  per-backend); only the assertion scaffold and fixtures are shared.

## Migration ordering & risk

1. **M1 first** (highest value, lowest risk): add `test/_shared/` to the
   conftest sys.path, move+rename the canonical module, repoint ~14 imports,
   delete 2 copies. Pure import-path change; no test logic touched.
2. **M2 + M3** (convention unification): mechanical loader/shim migration; each
   change is independently verifiable by running the affected skill's tests.
3. **M4 + M5** (sequence with D1 remediation): touch the build-backend test
   files, so land them together with the D1 Cluster A/D consolidation to avoid
   double-touching the same files.

**Risk controls**: every step is import-path or scaffold-extraction only — no
assertion semantics change. After each merge, the deleted module must have zero
remaining importers, and the full module-tests run (plus the plugin-doctor
test-convention rules) must stay green. The autouse isolation contract is
untouched throughout (Decision 1), so no test loses its sandbox.

## What this proposal deliberately does NOT do

- It does **not** introduce any package-scoped `conftest.py` (hard-rule
  compliance).
- It does **not** merge the genuinely skill-specific sibling helpers
  (`_layout_sim`, `_execution_manifest_fixtures`, `_doctor_fixtures`,
  `_handshake_fixtures`, `_plan_retrospective_fixtures`, `plugin-doctor/_fixtures`)
  — these are correctly skill-scoped and have no cross-bundle duplication.
- It does **not** collapse the per-backend `_CONFIG`/`CANONICAL_ARGS` — those are
  genuinely per-backend and must stay local.

## Cross-references

- Duplication findings this proposal resolves: `test-fixture-bootstrapping-inventory.md`
  (D2) findings D2-1 (M1), D2-2 (M2), D2-3 (M3).
- Redundancy clusters M4/M5 sequence with: `test-suite-redundancy-report.md`
  (D1) Clusters A and D.
- Prioritized, parallelizable remediation units incorporating these merges:
  `test-suite-remediation-map.md` (D4).
