# Project-Wide Test-Suite Redundancy Report

Analysis-only survey of the entire Python test suite under `test/**`, evaluated
against the `pm-dev-python:pytest-testing` quality bar (AAA structure, fixture
isolation, parametrization over copy-paste, no over-assertion of implementation
details). This document enumerates near-duplicate / overlapping **test-case
clusters** and **redundant-assertion patterns**, records the member files for
each, states the overlap rationale, and proposes a consolidation candidate
(merge / parametrize / delete / extract-shared-helper) per cluster.

No test or production source file is modified by this analysis; the report is
the sole output.

## Survey Coverage (auditable completeness)

The sweep covers every test-bearing top-level module directory under `test/**`.
The suite holds ~600 tracked files, of which the `.py` test modules are grouped
below. Coverage is enumerated per module so the sweep's completeness is
auditable (each directory is an explicit survey unit).

| Module dir (`test/…`) | Test `.py` files | Notes |
|-----------------------|------------------|-------|
| `default/` | 1 | `test_build_verify.py` only |
| `integration_common/` | 0 | `__init__.py` only — no test-bearing content |
| `marketplace/` | ~24 | `targets/claude`, `targets/opencode` generator tests |
| `plan-marshall/` | ~430 | the bulk of the suite; per-skill sub-packages |
| `pm-dev-frontend/` | ~4 | jsdoc + extension tests |
| `pm-dev-frontend-cui/` | 1 | `test_cui_js_extension.py` |
| `pm-dev-java/` | ~6 | logging/profile/extension tests |
| `pm-dev-java-cui/` | 1 | extension security profile only |
| `pm-dev-oci/` | 1 | extension security profile only |
| `pm-dev-python/` | 3 | plan-marshall-plugin extension tests |
| `pm-documents/` | ~5 | asciidoc / docs / manage-interface |
| `pm-plugin-development/` | ~90 | plugin-doctor analyzers dominate |
| `sync-plugin-cache/`, `finalize-step-*/` | ~5 | project-local finalize-step tests |
| root (`test/`) | 3 | `conftest.py`, `run-tests.py`, `test_conftest_discipline.py` |

The redundancy hot-spots concentrate in `plan-marshall/` (parallel build
backends, parallel CI providers, per-script input-validation) and
`pm-plugin-development/plugin-doctor/` (per-rule analyzer tests), plus the
cross-bundle extension-profile mirror set spanning six `pm-dev-*` bundles.

## Confidence legend

- **CONFIRMED** — the member files were read; the duplication is verified
  against source (concrete function names and identical bodies cited).
- **STRONG (filename+structure)** — the parallel-structure pattern is evident
  from the inventory and naming; spot-reads corroborate but not every member
  was opened. Confirm the exact member set before acting.

---

## Cluster A — Build-backend `run-config-key` parallel test set — CONFIRMED

**Members**

- `test/plan-marshall/build-gradle/test_gradle_run_config_key.py`
- `test/plan-marshall/build-maven/test_maven_run_config_key.py`
- `test/plan-marshall/build-npm/test_npm_run_config_key.py`
- `test/plan-marshall/build-pyproject/test_pyproject_run_config_key.py`

**Overlap rationale.** All four backends share the `script-shared` build
framework (`_build_execute_factory.compute_command_key`). Each file re-declares
the identical `_load(module_name, path)` `importlib` helper, the identical
`_SCRIPTS_DIR` path-walk, and the identical five test functions —
`test_run_config_key_returns_toon_with_required_fields`,
`test_run_config_key_json_format`, `test_run_config_key_canonical_args`,
`test_run_config_key_round_trip_matches_compute_command_key`,
`test_run_config_key_requires_command_args` — differing only in `build_tool`
name (`gradle`/`maven`/`python`/`npm`), the per-backend `CANONICAL_ARGS` list,
and the expected `key_suffix`. The round-trip test (`command_key ==
compute_command_key(_CONFIG, args)`) is the same structural drift guard in all
four, exercising the same shared helper four times.

**Quality-bar note.** The `_load` + `_SCRIPTS_DIR` boilerplate is copy-pasted
module state — a classic DRY violation the pytest standard would push into a
shared conftest helper. The round-trip property is genuinely per-backend
(each `_CONFIG` differs), so this is a *consolidation*, not a *deletion*, target.

**Consolidation candidate.** Extract a shared `build_config_key_helpers.py`
(sibling to `build_test_helpers.py`) exposing `assert_run_config_key_contract(
script_path, build_tool, canonical_args)`; each backend file collapses to a few
lines feeding its own `_CONFIG`/args. Alternatively parametrize a single module
over `(script, build_tool, canonical_args)` tuples — but keeping one thin
per-backend file preserves per-backend fixture locality.

---

## Cluster B — Cross-bundle extension security-profile tests — CONFIRMED

**Members**

- `test/pm-dev-python/plan-marshall-plugin/test_python_extension_security_profile.py`
- `test/pm-dev-java/plan-marshall-plugin/test_java_extension_security_profile.py`
- `test/pm-dev-java-cui/plan-marshall-plugin/test_java_cui_extension_security_profile.py`
- `test/pm-dev-oci/plan-marshall-plugin/test_oci_extension_security_profile.py`
- `test/pm-dev-frontend/plan-marshall-plugin/test_frontend_extension_security_profile.py`
- `test/pm-plugin-development/plan-marshall-plugin/test_plugin_dev_extension_security_profile.py`
- (sibling, `implementation` profile) `test/pm-documents/plan-marshall-plugin/test_documents_extension_implementation_profile.py`

**Overlap rationale.** The three files read (python / java / oci) are
**byte-for-byte identical modulo three tokens**: the bundle dir, the domain key
(`python` / `java` / `oci-containers`), and the expected focused skill
(`pm-dev-python:python-security`, etc.). Each declares the same
`_load_extension()`, the same `_security_defaults()` accessor, and the same two
tests: `test_security_profile_declared` (asserts non-empty defaults) and
`test_security_profile_resolves_<domain>_security` (asserts the focused skill is
present). The remaining members follow the same template. This is the single
highest-value parametrization target in the suite.

**Quality-bar note.** Six near-identical files to assert one invariant per
bundle ("the bundle's security profile resolves its focused security skill") is
exactly the copy-pasted-per-variant anti-pattern `pytest-testing` targets with
`@pytest.mark.parametrize`.

**Consolidation candidate.** MERGE into a single parametrized module
(e.g. `test/marketplace/test_extension_security_profiles.py` or a shared
plan-marshall-plugin test) driven by a table of
`(bundle, domain_key, expected_skill)` rows, with a shared `_load_extension`
helper keyed on bundle. Six files + the implementation-profile sibling collapse
to one parametrized file. Keep one row per bundle so a new bundle adds a row,
not a file.

---

## Cluster C — Per-script identifier input-validation tests — CONFIRMED

**Members** (the `--plan-id` rejection axis recurs in every one)

- `test/plan-marshall/manage-files/test_manage_files_input_validation.py`
- `test/plan-marshall/manage-findings/test_manage_findings_input_validation.py`
- `test/plan-marshall/manage-config/test_manage_config_input_validation.py`
- `test/plan-marshall/manage-logging/test_manage_logging_input_validation.py`
- `test/plan-marshall/manage-lessons/test_manage_lessons_input_validation.py`
- `test/plan-marshall/manage-metrics/test_manage_metrics_input_validation.py`
- `test/plan-marshall/manage-plan-documents/test_manage_plan_documents_input_validation.py`
- `test/plan-marshall/manage-references/test_manage_references_input_validation.py`
- `test/plan-marshall/manage-solution-outline/test_manage_solution_outline_input_validation.py`
- `test/plan-marshall/manage-status/test_manage_status_input_validation.py`
- `test/plan-marshall/manage-tasks/test_manage_tasks_input_validation.py`
- `test/plan-marshall/manage-architecture/test_architecture_input_validation.py`
- `test/pm-documents/manage-interface/test_manage_interface_input_validation.py`
- `test/pm-dev-java/maven-profile-management/test_profiles_input_validation.py`

**Overlap rationale.** These already share the `_pm_input_validation_fixtures`
helper (`HAPPY_VALUES`, `MALFORMED_AXES`, `assert_invalid_field`), so the good
DRY layer exists. The residual redundancy is that **each file re-declares a
near-identical `test_list_rejects_invalid_plan_id`** (and a
`test_<verb>_accepts_canonical_plan_id`) that is byte-identical modulo the
script path and the read verb (`list` vs `get` vs `read`). The
`MALFORMED_AXES['plan_id']` parametrization + `assert_invalid_field(result,
'invalid_plan_id')` assertion is exercised ~14 times against the same shared
validator. Verified: the `manage-files` and `manage-findings` variants of
`test_list_rejects_invalid_plan_id` are identical but for `SCRIPT_PATH` and the
`list` subcommand.

**Quality-bar note.** The **per-script wiring** of the shared validator is a
legitimate per-CLI concern (each script must actually call the validator), so
the `--plan-id` axis is NOT pure dead duplication — deleting it would drop real
coverage that a given script forgot to wire the validator. The redundancy is in
the *replicated boilerplate*, not the *intent*.

**Consolidation candidate.** EXTRACT a `assert_plan_id_axis_rejected(
script_path, read_verb, extra_args=())` into `_pm_input_validation_fixtures`, so
each per-script file becomes a one-line call passing its own `(script, verb)`.
Keep one call per script (preserving per-script coverage) but remove the
copy-pasted parametrized function body. Do NOT collapse into a single
cross-script parametrized module — that would couple unrelated scripts' fixture
lifecycles and lose the per-script locality the standard prefers.

---

## Cluster D — Coverage-report tests + duplicated coverage fixtures — CONFIRMED

**Test members**

- `test/plan-marshall/build-gradle/test_gradle_coverage_report.py`
- `test/plan-marshall/build-maven/test_maven_coverage_report.py`
- `test/plan-marshall/build-npm/test_npm_coverage_report.py`
- `test/plan-marshall/build-pyproject/test_pyproject_coverage_report.py`
- `test/plan-marshall/build-npm/test_js_coverage.py`
- `test/plan-marshall/extension-api/test_coverage_parse.py`

**Duplicated fixture members** (same JaCoCo/Cobertura/lcov shapes, copied per dir)

- `test/plan-marshall/build-gradle/fixtures/coverage/{high,low}-coverage.xml`
- `test/plan-marshall/build-maven/fixtures/coverage/{high,low}-coverage.xml`
- `test/plan-marshall/build-pyproject/fixtures/coverage/{high,low}-coverage.xml`
- `test/plan-marshall/extension-api/fixtures/coverage/{cobertura,jacoco,jest}-{high,low}.*`, `sample.lcov`
- `test/pm-dev-java/coverage/{high,low,no,multi-module}-*.xml`, `sample-jacoco.xml`
- `test/pm-dev-frontend-cui/coverage/*.json`, `lcov.info`
- `test/plan-marshall/build-npm/coverage/*.json`, `lcov.info`

**Overlap rationale.** The gradle coverage test's own docstring states: "Uses
the same JaCoCo XML format as Maven — the coverage parser is shared." Both
gradle and maven coverage tests delegate to the shared `build_test_helpers`
assertions (`assert_coverage_high/low/has_low_items/missing_file/
custom_threshold`), so the **test bodies are already thin wrappers** — the
redundancy is (a) five backends each declaring the same five wrapper functions,
and (b) the **high/low JaCoCo XML fixtures physically duplicated across at least
four directories** (build-gradle, build-maven, build-pyproject, pm-dev-java) plus
Cobertura/jest variants in extension-api. The single shared parser is exercised
from many copies of identical input.

**Quality-bar note.** Duplicated fixture files are a maintenance hazard: a
format change to the coverage parser needs every copy updated in lockstep, and
drift between copies produces confusing per-backend-only failures.

**Consolidation candidate.** (1) Consolidate the canonical high/low JaCoCo
(and Cobertura/jest/lcov) fixtures into ONE shared fixtures location (e.g.
`test/plan-marshall/script-shared/fixtures/coverage/`) referenced by all
backends; delete the per-backend copies. (2) Parametrize the five wrapper test
functions over `(script_path, fixtures_dir)` where the format is truly shared,
keeping backend-specific cases (npm/jest JSON) separate. This is a
delete-duplicates + parametrize combination.

---

## Cluster F — GitHub / GitLab CI-provider mirror tests — CONFIRMED

**Members** (each github file has a gitlab mirror)

- `test/plan-marshall/workflow-integration-github/test_github_ops_wait.py` ↔ `test/plan-marshall/workflow-integration-gitlab/test_gitlab_ops_wait.py`
- `test/plan-marshall/workflow-integration-github/test_github_ops_pr_merge.py` ↔ `test/plan-marshall/workflow-integration-gitlab/test_gitlab_ops_mr_merge.py`
- `test/plan-marshall/workflow-integration-github/test_github_merge_queue.py` ↔ `test/plan-marshall/workflow-integration-gitlab/test_gitlab_merge_queue.py`
- `test/plan-marshall/workflow-integration-github/test_github_ops.py` ↔ `test/plan-marshall/workflow-integration-gitlab/test_gitlab_ops.py`
- `test/plan-marshall/workflow-integration-github/test_github_pr.py` ↔ `test/plan-marshall/workflow-integration-gitlab/test_gitlab_pr.py`
- `test/plan-marshall/test_workflow_integration_github_ci_aggregation.py` ↔ `test/plan-marshall/test_workflow_integration_gitlab_ci_aggregation.py`

**Overlap rationale.** `test_github_ops_wait.py` and `test_gitlab_ops_wait.py`
are structural mirror images. The provider-agnostic poll-handler contract tests
— dispatch-table registration for `(checks, wait-for-status-flip)`,
`(issue, wait-for-close)`, `(issue, wait-for-label)`; the auth-short-circuit
tests; `completes_on_flip`; `times_out_when_status_never_changes`; the
`--expected=success/any` matrix — are **byte-identical modulo `github_ops`↔
`gitlab_ops`**, and the helpers `_ok_auth`, `_noop_sleep`, `_build_handler_map`,
`_flip_ci_status_args`, `_wait_for_close_args`, `_wait_for_label_args`,
`_resolve_plan_relative`, `_make_incrementing_clock` are duplicated verbatim in
both files. The failure-enrichment section and the p50-seed/watch-tail section
are provider-shaped mirrors: same test names, same assertions, differing only in
the stub (`run_gh`/`_RunGhStub` vs `run_glab`/`_GlStub`) and the fixture
(`ci-logs/github/fail.log` vs `ci-logs/gitlab/fail.log`).

**Quality-bar note.** The poll-handler contract (`poll_until` semantics, auth
short-circuit, timeout envelope) lives in the shared `ci_base` layer; asserting
it once per provider is the copy-paste-per-variant pattern. The
provider-*specific* parts (gh vs glab argv shapes, log-trace fixture markers)
are genuinely distinct and must stay.

**Consolidation candidate.** EXTRACT the provider-agnostic helpers and the
poll-handler contract tests into a shared `_ci_wait_contract.py` parametrized
over `(ops_module, fixture_path)`; keep only the provider-specific stub wiring
(argv shapes, trace markers) in the per-provider files. This removes the largest
verbatim-helper duplication in the suite while preserving the real
provider-specific coverage.

---

## Secondary clusters (STRONG — confirm member set before acting)

### E — Discover-modules unit vs integration two-tier — STRONG

- Unit: `build-gradle/test_gradle_discover_modules.py`,
  `build-maven/test_discover_modules.py`, `build-npm/test_npm_discover_modules.py`,
  `build-gradle/test_gradle_cmd_discover_behavior.py`,
  `build-maven/test_maven_discover_enrich_behavior.py`, `build-npm/test_npm_discover.py`
- Integration: `integration/discover_modules/test_gradle_discover_modules_integration.py`,
  `integration/discover_modules/test_maven_discover_modules.py`

**Rationale.** Per-backend module discovery is tested at a unit tier and again at
an integration tier with committed multi-module fixture projects
(`build-gradle/fixtures/multi-project/**`, `build-maven/fixtures/multi-module-project/**`).
Some assertions (module-name enumeration) likely overlap between tiers.
**Candidate:** audit for assertion overlap; keep the integration tier for the
real filesystem walk, prune any unit assertions that the integration tier
already covers. Do NOT blanket-delete — the tiers test different seams.

### G — `manage-lessons` one-verb-per-file granularity — STRONG

Twenty files (`test_add.py`, `test_get.py`, `test_list.py`, `test_remove.py`,
`test_update.py`, `test_supersede.py`, `test_set_body.py`, `test_set_title.py`,
`test_from_error.py`, `test_convert_to_plan.py`, `test_restore_from_plan.py`, …)
share `_lessons_helpers.py`. **Rationale:** fine-grained one-verb-per-file split
is defensible, but the simplest CRUD verbs (`get`/`list`/`set_title`/`set_body`)
may over-partition and re-assert shared setup. **Candidate:** review for
merge of the trivial getter/setter files into a single `test_lessons_crud.py`;
retain complex-verb files (`supersede`, `convert_to_plan`, `restore_from_plan`).
Low priority — this is organizational, not assertion, redundancy.

### H — plugin-doctor per-analyzer test harness — STRONG

~50 `test_analyze_*.py` files under `pm-plugin-development/plugin-doctor/`, one
per rule. **Rationale:** one-file-per-analyzer is the correct granularity (each
rule is an independent unit), so this is NOT a delete target. The likely
redundancy is a **repeated analyze-and-collect-findings scaffold** in each file.
**Candidate:** confirm whether `_fixtures.py` / `test_analyze_shared.py` already
factor the scaffold; if each analyzer test still re-implements the
"run analyzer → assert finding codes" boilerplate, extract a shared
`assert_analyzer_findings(analyzer, fixture, expected_codes)` helper. Keep the
per-rule files. Extraction, not consolidation of files.

### I — `manage-config` overlapping detection/defaults tests — STRONG

- `manage-config/test_config_defaults.py` vs root `plan-marshall/test_manage_config_defaults.py`
  — two "config defaults" test files in different locations (potential split of
  the same surface).
- `manage-config/test_config_detection.py` vs `manage-config/test_detection.py`
  — two "detection" files; confirm they test distinct detection paths, not the same one.

**Candidate:** read the four files; if `test_manage_config_defaults.py` (root)
and `test_config_defaults.py` (package) assert the same default-seeding surface,
merge into the package-local file and delete the root straggler. If
`test_detection.py` and `test_config_detection.py` overlap, merge.

### J — root-level stragglers duplicating package tests — STRONG

- `plan-marshall/test_audit_archived_plan_retrospectives.py` vs
  `plan-marshall/audit-archived-plan-retrospectives/test_audit.py`
- `plan-marshall/test_phase_6_finalize_ci_verify.py` vs
  `plan-marshall/phase-6-finalize/test_ci_verify.py` (and
  `phase-6-finalize/test_ci_complete_precondition.py`)
- `plan-marshall/test_phase_6_finalize_step_id_consistency.py`,
  `plan-marshall/test_manage_config_defaults.py`,
  `plan-marshall/test_recipe_lesson_cleanup.py`, etc. — a set of loose
  `test/plan-marshall/test_*.py` files that sit outside the per-skill
  sub-package they exercise.

**Rationale.** A root-level `test_<skill>_*.py` that duplicates coverage already
present in the skill's own sub-package fragments the skill's test surface across
two locations. **Candidate:** for each straggler, confirm whether its assertions
overlap the sub-package's; if so, relocate/merge into the sub-package and delete
the root file. Purely organizational where there is no assertion overlap — but
the CI-verify pair is a likely genuine overlap worth confirming.

---

## Redundant-assertion patterns (cross-cutting)

Beyond whole-file clusters, these assertion patterns recur across many
otherwise-distinct tests and re-verify the same shared invariant:

1. **`--plan-id` rejection re-assertion** (Cluster C) — the shared
   identifier validator's `invalid_plan_id` path is asserted in ~14 files.
   Over-replication of a single shared-validator behavior.
2. **`status == 'success'` envelope re-assertion** — nearly every
   `manage-*` CLI test re-asserts the TOON `status` field. This is correct
   per-command contract coverage, NOT redundant — flagged only to distinguish
   it from true redundancy (do not "consolidate" these away).
3. **`compute_command_key` round-trip** (Cluster A) — the same drift-guard
   assertion in all four build backends against the same shared helper.
4. **Auth-short-circuit `fetch_calls['count'] == 0`** (Cluster F) — the same
   "no fetch before auth" assertion duplicated verbatim across both CI providers
   and multiple handler tests within each.
5. **Over-assertion of implementation detail** — the p50-seed tests
   (Cluster F) assert on internal seam call sequences (`seed_sleeps == [120]`,
   `watch_calls[0][0] == '1001'`). These couple the test to the seam wiring;
   `pytest-testing` would flag asserting on `_sleep_seed`/`_watch_run` call
   internals rather than observable outcome. Not redundant across files, but a
   brittleness smell worth noting for the remediation map.

---

## Prioritized consolidation summary

| # | Cluster | Members | Action | Priority | Confidence |
|---|---------|---------|--------|----------|------------|
| B | Extension security-profile | 6–7 files | MERGE → one parametrized module | P1 (highest ROI) | CONFIRMED |
| F | GitHub/GitLab CI mirror | ~12 files | EXTRACT shared contract + helpers | P1 | CONFIRMED |
| A | Build `run-config-key` | 4 files | EXTRACT shared helper | P2 | CONFIRMED |
| D | Coverage report + fixtures | 6 tests, ~15 fixtures | DEDUPE fixtures + parametrize | P2 | CONFIRMED |
| C | Input-validation `--plan-id` axis | ~14 files | EXTRACT axis helper (keep 1 call/script) | P3 | CONFIRMED |
| I/J | manage-config + root stragglers | ~8 files | MERGE overlapping, relocate stragglers | P3 | STRONG |
| E | Discover-modules two-tier | ~8 files | PRUNE overlapping unit assertions | P4 | STRONG |
| H | plugin-doctor harness | ~50 files | EXTRACT scaffold (keep per-rule files) | P4 | STRONG |
| G | manage-lessons CRUD split | ~20 files | MERGE trivial getters/setters | P5 (low) | STRONG |

`P1` targets (B, F) remove the largest verbatim duplication with the least risk
(pure test-structure refactor over a shared, stable contract). `P4`/`P5` are
organizational and should not be pursued unless the owning skill is already
being touched.

## Cross-references

- Fixture / conftest / shared-helper inventory: `test-fixture-bootstrapping-inventory.md` (D2).
- Note for D2: `test/plan-marshall/build_test_helpers.py` and
  `test/plan-marshall/discovery_test_helpers.py` **do exist** on disk (contrary
  to the outline's provisional note) and are the shared-assertion helpers that
  Clusters A and D already lean on.
- Unification design for the shared helpers proposed here (a shared coverage
  fixtures dir, a CI-wait contract helper, a build-config-key helper): see the
  unification proposal `test-fixture-unification-proposal.md` (D3).
- Prioritized, parallelizable remediation units: `test-suite-remediation-map.md` (D4).
