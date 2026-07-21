# Prioritized Test-Suite Remediation Map

The plan's headline deliverable. Synthesizes the redundancy report (D1), the
fixture inventory (D2), and the unification proposal (D3) into a single
actionable, prioritized remediation map. It partitions the project-wide
test-package groups into remediation units, tags each as a standards-compliance
target or a hardening-propagation target, assigns a priority, and flags
surface-disjoint package pairs eligible for parallel remediation.

Analysis-only — no remediation is implemented here. Every unit below is a
proposal that traces back to a D1–D3 finding.

## Tagging model

- **compliance** — the unit does not yet meet `pm-dev-python:pytest-testing`
  (copy-paste-per-variant instead of parametrize, duplicated fixtures, brittle
  implementation-detail assertions). Remediation brings it up to the bar.
- **hardening-propagation** — the unit already embodies a hardened pattern
  (shared helper, autouse isolation, parametrization) that should be *propagated*
  to units that lack it. These are the templates, not the problems.
- **infra** — a shared-infrastructure change (conftest sys.path, shared-fixture
  relocation) that unblocks multiple compliance units.

Priority: **P1** highest ROI / lowest risk → **P5** organizational / optional.

## Remediation units

### RU-0 — Shared-fixture infrastructure (`test/conftest.py` + `test/_shared/`) — infra, P1

**Surface**: `test/conftest.py` (add `test/_shared/` to sys.path), new
`test/_shared/_input_validation_fixtures.py`.
**Trace**: D2-1, D3 Decision-1 corollary + M1.
**Action**: land the sys.path addition and the canonical shared module FIRST —
it unblocks RU-1. Pure infra; no test-body change.
**Blocks**: RU-1. **Blocked by**: nothing.

### RU-1 — Input-validation fixture de-duplication — compliance, P1

**Surface (package group)**: every `*_input_validation.py` across
`manage-*` (plan-marshall), `pm-dev-java/maven-profile-management`,
`pm-documents/manage-interface`; deletes the 2 bundle fixture copies.
**Trace**: D1 Cluster C, D2-1, D3 M1.
**Action**: repoint ~14 imports to `test/_shared/_input_validation_fixtures`;
delete `_maven_profile_input_validation_fixtures.py` and
`_manage_interface_input_validation_fixtures.py`.
**Blocked by**: RU-0.

### RU-2 — Cross-bundle extension-profile parametrization — compliance, P1

**Surface**: the 6 `test_*_extension_security_profile.py` files (pm-dev-python,
pm-dev-java, pm-dev-java-cui, pm-dev-oci, pm-dev-frontend, pm-plugin-development)
+ the pm-documents implementation-profile sibling.
**Trace**: D1 Cluster B (byte-identical-modulo-name, highest-ROI parametrization).
**Action**: MERGE into one parametrized module driven by
`(bundle, domain_key, expected_skill)` rows with a shared `_load_extension`.
**Blocked by**: nothing (self-contained, no shared-fixture dependency).

### RU-3 — CI-provider contract extraction (github/gitlab) — compliance, P1

**Surface**: `workflow-integration-github/*` ↔ `workflow-integration-gitlab/*`
mirror pairs (wait, ops, pr-merge, merge-queue, pr, ci-aggregation).
**Trace**: D1 Cluster F (verbatim helper + poll-handler duplication).
**Action**: EXTRACT the provider-agnostic helpers + poll-handler contract tests
into a shared `_ci_wait_contract.py` parametrized over `(ops_module, fixture)`;
keep provider-specific stub wiring local.
**Blocked by**: nothing.

### RU-4 — Build-backend test consolidation — compliance, P2

**Surface**: `build-gradle`, `build-maven`, `build-npm`, `build-pyproject`
`test_*_run_config_key.py` + `test_*_coverage_report.py` + shared coverage
fixtures.
**Trace**: D1 Clusters A + D, D2-2, D3 M4 + M5.
**Action**: extend `build_test_helpers.py` with
`assert_run_config_key_contract(...)`; dedupe JaCoCo fixtures into
`script-shared/fixtures/coverage/`; migrate the four backends' wrapper functions.
**Scope**: RU-4 intentionally scopes to the JaCoCo `{high,low}-coverage.xml`
fixture subset of Cluster D (the shape shared by the four build backends'
JaCoCo parser). **Out of scope** — requiring separate remediation units because
their formats differ from JaCoCo XML: `build-npm`'s lcov/json fixtures,
`extension-api`'s Cobertura/jest fixtures, and `pm-dev-frontend-cui`'s lcov/json
fixtures.
**Blocked by**: nothing (build_test_helpers already on sys.path).

### RU-5 — Loader/sys.path convention unification — compliance, P2

**Surface**: `_arch_fixtures.py`, `_lessons_helpers.py`, `_handshake_fixtures.py`,
`_plan_retrospective_fixtures.py` (open-coded importlib + sys.path shims).
**Trace**: D2-2, D2-3, D3 M2 + M3.
**Action**: migrate open-coded `_load` to `conftest.load_script_module`; delete
the redundant `toon_parser` sys.path shim in `_plan_retrospective_fixtures.py`;
centralize the remaining script-reach shims.
**Blocked by**: nothing (uses existing conftest API).

### RU-6 — plugin-doctor analyzer test-scaffold extraction — hardening-propagation, P4

**Surface**: `pm-plugin-development/plugin-doctor/test_analyze_*.py` (~50 files).
**Trace**: D1 Cluster H.
**Action**: confirm whether each analyzer test still re-implements the
"run analyzer → assert finding codes" scaffold; if so, extract a shared
`assert_analyzer_findings(...)`. KEEP the per-rule files (correct granularity).
This unit's `_fixtures.py` firing-corpus is itself a hardened pattern worth
propagating (one known-defect fixture per rule).
**Blocked by**: nothing.

### RU-7 — discover-modules two-tier assertion pruning — compliance, P4

**Surface**: `build-*` unit `discover_modules` tests + `integration/discover_modules/*`.
**Trace**: D1 Cluster E.
**Action**: audit unit-vs-integration assertion overlap; prune unit assertions
the integration tier already covers. Do NOT blanket-delete (different seams).
**Blocked by**: nothing.

### RU-8 — manage-config detection/defaults + root-straggler consolidation — compliance, P3

**Surface**: `manage-config/test_config_defaults.py` vs root
`test_manage_config_defaults.py`; `test_config_detection.py` vs
`test_detection.py`; the loose `test/plan-marshall/test_*.py` stragglers
(`test_phase_6_finalize_ci_verify.py`, `test_audit_archived_plan_retrospectives.py`,
etc.).
**Trace**: D1 Clusters I + J.
**Action**: confirm assertion overlap; merge overlapping pairs; relocate
stragglers into their skill sub-package.
**Blocked by**: nothing.

### RU-9 — manage-lessons CRUD file consolidation — compliance, P5 (optional)

**Surface**: the 20 `test_manage_lessons_*` per-verb files.
**Trace**: D1 Cluster G.
**Action**: merge trivial getter/setter files (`test_get`, `test_list`,
`test_set_title`, `test_set_body`) into one `test_lessons_crud.py`; retain
complex-verb files. Organizational only — pursue only if the skill is already
being touched.
**Blocked by**: nothing.

## Priority-ordered summary

| Unit | Tag | Priority | Blocked by | Cross-ref |
|------|-----|----------|------------|-----------|
| RU-0 shared-fixture infra | infra | P1 | — | D2-1, D3 M1 |
| RU-1 input-validation dedupe | compliance | P1 | RU-0 | D1-C, D2-1 |
| RU-2 extension-profile parametrize | compliance | P1 | — | D1-B |
| RU-3 CI-provider contract extract | compliance | P1 | — | D1-F |
| RU-4 build-backend consolidation | compliance | P2 | — | D1-A/D |
| RU-5 loader/sys.path unification | compliance | P2 | — | D2-2/3 |
| RU-8 manage-config + stragglers | compliance | P3 | — | D1-I/J |
| RU-6 plugin-doctor scaffold | hardening-propagation | P4 | — | D1-H |
| RU-7 discover-modules pruning | compliance | P4 | — | D1-E |
| RU-9 manage-lessons CRUD merge | compliance | P5 | — | D1-G |

## Surface-disjoint parallelizable pairs

Two units are parallelizable when their file sets do not overlap AND they do not
edit the same shared fixture. The following pairs (and the larger parallel wave)
are safe to remediate concurrently:

| Parallel set | Units | Disjointness proof |
|--------------|-------|--------------------|
| **Wave A (after RU-0)** | RU-2 ∥ RU-3 ∥ RU-4 | RU-2 touches only `pm-dev-*/plan-marshall-plugin/*` + `pm-documents/plan-marshall-plugin/*`; RU-3 touches only `workflow-integration-{github,gitlab}/*`; RU-4 touches only `build-*/*` + `script-shared/fixtures/`. Three disjoint directory subtrees, no shared fixture. |
| **Pair** | RU-2 ∥ RU-1 | RU-2 edits extension-profile tests; RU-1 edits `*_input_validation.py`. No file overlap. RU-1 waits on RU-0 (fixture home) but RU-2 has no fixture dependency — safe concurrent. |
| **Pair** | RU-3 ∥ RU-5 | RU-3 edits CI-provider test bodies; RU-5 edits sibling `_*.py` loaders in `manage-architecture`/`manage-lessons`/`plan-marshall`/`plan-retrospective`. Disjoint. |
| **Pair** | RU-6 ∥ RU-7 | RU-6 = plugin-doctor analyzer tests; RU-7 = build-* discover-modules tests. Disjoint subtrees. |
| **Pair** | RU-8 ∥ RU-9 | RU-8 = manage-config + root stragglers; RU-9 = manage-lessons CRUD files. Disjoint. |

**NOT parallelizable** (serialize):

- **RU-0 → RU-1** — RU-1 imports the module RU-0 creates. Hard dependency.
- **RU-4 ∦ RU-5 on the build backends** — RU-4 rewrites `test_*_run_config_key.py`
  wrappers and RU-5 migrates their `_load` importlib helper; both touch the same
  four build-backend files. Land RU-4 first (it removes the `_load` as a side
  effect), then RU-5 covers the remaining non-build loaders.
- Any two units touching `build_test_helpers.py` (RU-4) must serialize against
  each other's edits to that single shared helper.

## Recommended execution sequence

1. **RU-0** (infra, unblocks RU-1).
2. **Wave A in parallel**: RU-2, RU-3, RU-4 (three disjoint subtrees) + RU-1
   (once RU-0 lands).
3. **RU-5** after RU-4 (build-backend loader overlap).
4. **RU-8** (independent, any time).
5. **Wave B in parallel**: RU-6 ∥ RU-7 (both P4, disjoint).
6. **RU-9** last (P5, optional).

Each unit is independently verifiable: run the affected skill's module-tests and
confirm the plugin-doctor test-convention rules (`unique-fixture-basenames`,
`subprocess-pythonpath`) stay green. The autouse isolation contract
(`test/conftest.py`) is never modified except by RU-0's additive sys.path entry,
so no unit loses its sandbox.

## Traceability

- Redundancy clusters (A–J): `test-suite-redundancy-report.md` (D1).
- Fixture/bootstrapping inventory + divergence findings (D2-1..D2-5):
  `test-fixture-bootstrapping-inventory.md` (D2).
- Unification design (merge map M1–M5, per-consumer migration):
  `test-fixture-unification-proposal.md` (D3).
