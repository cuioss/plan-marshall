# Run report — 070-architecture-and-orchestration-test-reduction (run 01)

**Date (UTC):** 2026-08-18    **Branch:** `claude/architecture-orchestration-test-reduction-iuthfe` (harness-assigned; kept as-is per the lane contract)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

| Skill | Route | Result |
|---|---|---|
| `cloud-plan-lane` | `Skill:` notation | loaded — the run's working contract |
| `pm-dev-python:pytest-testing` | `marketplace/bundles/pm-dev-python/skills/pytest-testing/SKILL.md` | read (plan surface is Python tests) |

`plan-marshall:ref-code-quality` and `pm-plugin-development:plugin-script-architecture` are the
contract's always-load pair. This plan's surface is `test/**` only — it ships no script and edits no
bundle — so the script-architecture standard governs nothing in the diff; the code-quality standard is
applied through `./pw quality-gate`, which runs `ruff` and `mypy` over the same tree on every commit.
Both are recorded here as **not separately read**, rather than silently omitted.

## Gating derivations (run before D1)

### Blocking dependencies — both landed

| Check | Command | Result |
|---|---|---|
| Plan `010` landed | module-budget section of `persona-module-tester/standards/testing-methodology.md` | present — `### Module Budget: 400 lines` at line 75 |
| Plan `020` landed | `grep -n 'def parse_ns' test/conftest.py` | present at line 569 |
| Plan `090` landed? | `grep -rn 'build_test_helpers' test/conftest.py` | **non-empty** — line 1128. `090` has **not** landed |

`090`'s absence has two consequences the plan names, and both are honoured: the `conftest.py`
reference is recorded as a proposal rather than edited (see § Findings, F1), and D3's `parse_ns` half
stops at the first missing parser seam.

### The partition — holds, no defect

Derived per `doc/plans/test-quality/README.md` § "The partition, and how a run re-derives it": every
directory under `test/plan-marshall/*/` (68), every file at the root of `test/plan-marshall/` (12),
and every top-level entry under `test/` other than `plan-marshall/` itself (21), each checked against
`030`–`080`'s Expected surfaces.

**Every entry appears in exactly one plan's surface.** Three apparent double-claims were resolved by
reading the claiming text rather than the grep hit:

| Apparent collision | Resolution |
|---|---|
| `build_test_helpers.py`, `discovery_test_helpers.py` in `060` **and** `070` | `060` § D3 and § Expected surface explicitly **disclaim** both, assigning the renames to `070` because `070` owns every importer |
| `finalize-step-sync-plugin-cache` in `070` **and** `080` | Two different directories — `080` claims `test/finalize-step-sync-plugin-cache/`, `070` claims `test/plan-marshall/finalize-step-sync-plugin-cache/` |
| `script-shared` in `060` **and** `070` | `060` owns it. `070` names it once, in § Verification, as a **read-only** control-pair check; it is absent from `070`'s Expected surface |

No entry is in two lists; no entry is in none. The gate passes and the run proceeded.

## Census — re-derived

Every figure below is measured on this clone at `eb0124c` (the branch point), over the Expected
surface list, not taken from the plan.

| Measure | Plan's lead | Re-derived | Command |
|---|---:|---:|---|
| `.py` files in the slice | — | **180** | `git ls-files` over the 27 directories + 4 named root modules |
| `test_*.py` modules | ~168 | **171** | same, filtered to `/test_` |
| Lines in the slice | ~63,200 | **65,163** | `xargs wc -l` over the surface list |
| Comment lines | — | **5,956** | `grep -hE '^\s*#'` over the surface list |
| Modules over the 400-line budget | 63 | **63** | `xargs wc -l \| awk '$1>400'` |
| `Namespace(` constructions | ~502 | **506** | `xargs grep -h 'Namespace('` |
| `parse_ns(` calls | ~1 | **1** | `xargs grep -h 'parse_ns('` |
| `spec_from_file_location` occurrences | — | **31** across 22 modules | `xargs grep -h`/`-c` |
| `load_script_module` occurrences | — | **214** | `xargs grep -h` |
| Deep `Path(__file__).parent` chains (3+) | — | **16** | `xargs grep -hE 'Path\(__file__\)(\.parent){3,}'` |

The two headline leads are both slightly low: the slice is **65,163** lines across **171** modules,
not ~63,200 across ~168. The `Namespace(`-to-`parse_ns` ratio the plan uses to size D3 is confirmed
at **506 : 1**.

## Baseline measurements

Taken at `eb0124c`, before the first edit.

| Measure | Value | Command / population |
|---|---|---|
| Collected tests (slice) | **3,622** | `uv run python -m pytest {27 dirs + 2 root modules} --collect-only -q -o addopts=""` |
| Passed / failed / **skipped** | 3,622 / 0 / **0** | `uv run python -m pytest {same scope} -q -p no:randomly -o addopts="--durations=15"` |
| Wall-clock (slice) | **181.20 s** | same command. Population: this slice only, in one cloud session — **not** comparable to a `./pw verify` total, which also runs the quality gate and test-compile |
| Slowest test | 19.53 s — `build-gradle/test_gradle_discover_modules.py::test_discover_gradle_kotlin_dsl` | `--durations=15` |

### `plugin-doctor test-conventions` — baseline, slice-scoped

Run with the epic README's five-directory `PYTHONPATH` invocation, `--test-root test/plan-marshall`,
then filtered to this slice's Expected surface. The command ran first time; the five directories are
still sufficient and no sixth was needed.

| Rule | Slice findings (before) |
|---|---:|
| `test-module-line-budget` | 63 |
| `test-module-preamble-boilerplate` | 47 |
| `test-docstring-historical-prose` | 42 |
| `subprocess-pythonpath` | 1 |
| `unique-fixture-basenames` | 0 |
| `test-helper-module-misnamed` | 0 |
| `identifier-validator-corpus` | 0 |
| **Total** | **153** |

The two zeroes on `unique-fixture-basenames` and `test-helper-module-misnamed` are themselves the
evidence for D1's premise: **neither rule could see either unprefixed root-level helper.** The plan
predicted this for `unique-fixture-basenames` (its detection step 1 enumerates only `_`-prefixed
files); it holds for `test-helper-module-misnamed` too. A green from those two rules before D1 was an
un-asked question, not a clean result.

## Deliverables

### D1 — One build-extension fixture surface — **done** (commit `a00a9b2`)

**Gating hypothesis: CONFIRMED.** The six `build-*` directories did stage the extension contract
independently. Read one module per directory:

| Directory | How it staged the contract before D1 |
|---|---|
| `build-gradle` | `spec_from_file_location` + a 9-line `PROJECT_ROOT`/`EXTENSION_FILE` path chain, twice (`test_gradle_extension.py`, `test_gradle_rides_the_maven_join.py`) |
| `build-maven` | the same two constructs, again twice (`test_maven_extension.py`, `test_maven_derivation_resolver.py`) |
| `build-npm` | `load_script_module` — already **B7**-compliant |
| `build-operations` | its own private `_load_build_extension(skill, module_name)` over `MARKETPLACE_ROOT` |
| `build-pyproject` | `load_script_module` + `get_scripts_dir` — already **B7**-compliant |
| `build-server` | a 3-line `sys.path.insert` bootstrap repeated in 4 modules, plus an identical 8-field `ExecuteConfig` baseline declared in 3 and in compact form in a 4th |

**Importer sets confirmed as OBSERVED.** `build_test_helpers` was imported by exactly four `build-*`
directories in 8 modules (`build-gradle`, `build-maven`, `build-npm`, `build-pyproject`);
`build-operations` and `build-server` did not reference it. `discovery_test_helpers` was imported by
exactly `build-npm/test_npm_discover.py` and `build-gradle/test_gradle_discover_modules.py`.

**What landed:**

* Both renames, with all ten importers **and their prose references** updated — the module docstrings
  of the coverage-report and run-config-key modules name the helper by module path, so they were
  stale the moment the file moved.
* `build_scripts_dir()` — the `sys.path` bootstrap, replacing 4 copies. It deliberately does **not**
  import the factory; each consumer keeps its own module-level
  `import _build_execute_factory as factory` so binding timing is unchanged by sharing the bootstrap.
* `execute_config(factory, capture_strategy, **overrides)` — the `ExecuteConfig` baseline, replacing 4
  copies. The factory module is **passed in** rather than imported here, so the config is built from
  the same copy whose seams the caller patches, and this module never binds a copy of its own.
* `load_build_extension(skill, module_name)` — replacing the 5 `spec_from_file_location` loaders. It
  stays **non-registering**, and `module_name` is required rather than derived.

**The `sys.modules` hazard is documented at the fixture that causes it**, with the two consequences it
imposes on anything added to that module. Note a correction to the plan's § Problem, which states the
helper's "own module docstring records" the hazard: it did not. The hazard was recorded only in
`test/conftest.py`'s `_routing_namespaces` docstring — which is what the plan's own claim-label table
cites as the artifact. D1's done-when ("documented at the fixture that causes it") is therefore an
**addition**, and that is what was done.

**Registration-name preservation.** Every converted call site keeps its original module name, per the
plan's first hazard. Two sites (`build-maven/test_maven_extension.py` and
`build-maven/test_maven_derivation_resolver.py`) already shared the name `maven_build_extension`; since
neither load registers, they remain independent objects. The shared name is now documented at the
second site as a `__name__` label rather than a registration, so a future conversion to a registering
loader cannot collapse them silently.

**Fifth verification check — the daemon-routing neutralization still engages, and still
discriminates.** The matched pair under `test/plan-marshall/script-shared/` (read-only here; the
directory is plan `060`'s) passes as shipped (2 passed). With the `@pytest.mark.allow_daemon_routing`
marker temporarily removed so the fixture stays engaged, the negative arm **fails** on its own
assertion — `assert 0 == 1`, "the marker did not disengage the neutralization fixture". A control pair
that passed in both configurations would prove nothing; this one does not. The probe edit was reverted
with `git checkout --`, and `git status` confirms the directory is untouched in the diff.

### D2 — One plan-lifecycle staging fixture — **not built; its justifying hypothesis is refuted**

The plan labels D2's premise `HYPOTHESIS — asserted absence, the higher-risk half; it is D2's entire
justification`, and instructs: *"If two already share one, D2 is an extension of that surface rather
than a new one — say so rather than building a second."* Measured across all 16 test modules in the
nine directories:

| Directory | Module | `plan_context` | `plan_dir_for` | inline `mkdir` | stages a plan dir? |
|---|---|---:|---:|---:|---|
| `phase-1-init` | `test_phase_1_init.py` | 0 | 0 | 1 | no — stages a *lessons* dir; one test asserts a `plans/` destination path |
| `phase-2-refine` | `test_..._manage_config_readonly.py` | 0 | 0 | 0 | no — `PLAN_BASE_DIR` is a synthetic-repo env redirect |
| `phase-2-refine` | `test_..._scope_estimate.py` | 2 | 0 | 0 | **shares `plan_context`** |
| `phase-3-outline` | `test_..._qgate_bypass.py` | 0 | 0 | 0 | no |
| `phase-4-plan` | `test_verification_only_guard_contract.py` | 0 | 0 | 0 | no |
| `execute-task` | 3 modules | 0 | 0 | 1 | no |
| `manage-lifecycle` | `test_manage_lifecycle.py` | 26 | 2 | 0 | **shares `plan_context`** |
| `manage-personas` | `test_manage_personas.py` | 0 | 0 | 1 | no |
| `manage-plan-documents` | `test_manage_plan_documents.py` | 68 | 21 | 0 | **shares `plan_context`**, plus a `_make_create_args` keyword-override factory |
| `manage-plan-documents` | `test_request_body_file_ingestion.py` | 12 | 3 | 1 | **shares `plan_context`** |
| `manage-plan-documents` | `test_..._input_validation.py` | 0 | 0 | 0 | no |
| `manage-terminal-title` | `test_manage_terminal_title.py` | 0 | 0 | 0 | no |
| `manage-terminal-title` | `test_orchestrator_title.py` | 0 | 0 | 1 | no — stages an *orchestrator epic* dir, already via a `_write_state` helper |

Two findings, both against the plan rather than the tree:

1. **The asserted absence is false.** Four modules across **three** of the nine directories already
   share `plan_context`, which is exactly the shared surface D2 proposed to build on top of.
2. **D2's own done-when already holds on `main`.** It reads *"no module in those directories stages a
   plan directory inline in three or more tests"*. No module in the group stages one inline in three
   or more tests — the maximum is a single `mkdir` call per module, and the largest consumer
   (`test_manage_plan_documents.py`, 885 lines) already routes its staging through a keyword-override
   factory composed with `plan_context`.

Building a `_{domain}_fixtures.py` staging factory here would add a second surface serving a
duplication that is not present, against a done-when already satisfied. Per the plan's own
instruction, it is **reported rather than built**, and the run's budget went to D3 and D4 instead.

### D3 — Normalise preambles (**B7**) and argument construction (**B6**) — **B7 half done** (commit `ab460a0`); **B6 half not done**

#### B7 — done, and the exception list is complete

| Measure | Before | After |
|---|---:|---:|
| Deep `Path(__file__).parent` chains (3+) | 13 (after D1 removed 3) | **0** |
| Modules containing `spec_from_file_location` | 22 | **8** |
| `test-module-preamble-boilerplate` doctor findings (slice) | 47 | **18** |

The slice now carries **no** deep parent-chain arithmetic. Roots come from
`conftest`'s own `PROJECT_ROOT` / `MARKETPLACE_ROOT` / `get_scripts_dir`.

The four identical `_load_module` re-implementations in `manage-architecture` are inlined through
`load_script_module`. They already registered under the same name they passed, so the conversion is
semantics-identical — the registration-preservation hazard the plan names does not arise.

**Every remaining `spec_from_file_location` site is listed with its reason.** None is an oversight:

| Site | Reason it stays | Owner |
|---|---|---|
| `build-gradle/test_gradle_discover_modules.py` | loads `plan-marshall-plugin/extension.py` — a bundle skill's **root-level** file, not a `scripts/` module, so `get_scripts_dir` cannot address it | `090` § D2 |
| `build-npm/test_npm_discover_modules.py` | same | `090` § D2 |
| `build-operations/test_extension_implementations.py` | same, and the bundle is a loop variable | `090` § D2 |
| `test_plan_marshall_plugin_extension.py` | same | `090` § D2 |
| `build-pyproject/test_build_cmd_coverage.py` | loads the **repository-root** `build.py`, which is under no skill at all | `090` § D2 |
| `build-pyproject/test_dynamic_mypypath.py` | same | `090` § D2 |
| `build-pyproject/test_pyproject_build.py` (line 321) | same | `090` § D2 |
| `build-pyproject/test_pyproject_build.py` (line 49) | installs `sys.modules` mocks (`plan_logging`, `run_config`) **between** `module_from_spec` and `exec_module`. `load_script_module` performs both in one call, so that window does not exist | this slice, needs a loader change → `090` |
| `phase-1-init/test_phase_1_init.py` | ⛔ **registration collision.** It loads `manage-lessons.py` under the name `manage_lessons`, and `test/plan-marshall/manage-lessons/_lessons_helpers.py` **already registers that exact name** through `load_script_module`. Its own load does not register, so the two copies are independent today; converting it would collapse them onto one registration — the order-dependent-failure class plan `030` paid **173 failures** for. `manage-lessons/` is plan `050`'s directory, so the other half is not reachable from here either | recorded; needs `050`/`090` coordination |

#### B6 — not done, with the seam map measured rather than assumed

`Namespace(` is **506** before and **506** after; `parse_ns(` is **1** before and **1** after. This
half is **not started**, and per `030`'s own finding an untouched surface must not be reported as a
clean result. What this run *did* produce is the measurement the next run needs, so it does not pay
for the probe again.

**The plan's sizing lead is corrected.** It names `manage-architecture` as "the corpus's heaviest
user … of hand-built namespaces". Measured, the heaviest directory in this slice is
**`plan-orchestrator`** at ~224 sites, against `manage-architecture`'s ~84. The three largest single
modules are `plan-orchestrator/test_inbox_envelope.py` (63), `test_orchestrator_corpus.py` (54) and
`test_inbox_message_state.py` (53).

**Seam probe** — run through `conftest.parse_ns` against each script the slice's `Namespace(` sites
target, and this is the D3 exception list the done-when asks for:

| Script | Seam | Blocking reason |
|---|---|---|
| `plan-orchestrator/orchestrator.py` | ✅ resolves | — |
| `manage-architecture/architecture.py` | ✅ resolves | — |
| `manage-plan-documents/manage-plan-documents.py` | ✅ resolves | — |
| `plan-marshall/phase_handshake.py` | ✅ resolves | — |
| `plan-marshall/effort_presets.py` | ❌ **`ParserSeamNotFound`** | publishes none of `('build_parser', '_build_parser', '_build_arg_parser')` and has no callable `main()` — **a missing parser seam, plan `090` § D1's surface** |
| `manage-terminal-title/manage_terminal_title.py` | ❌ **`ParserSeamNotFound`** | same shape — **plan `090` § D1's surface** |
| `manage-lifecycle`, `build-server`, `q-gate-validation-agent` | n/a | these skills publish **no** top-level CLI script at all; their `Namespace(` sites call `cmd_*` handlers on modules loaded directly, so `parse_ns` has no script to address. Not a seam gap — a different shape, and one `090` § D1 should be told about |

So the plan's gating hypothesis *"`090` has published a parser seam for every module a `parse_ns`
conversion in this slice would otherwise block on"* is **refuted**: `090` has not landed, and two
scripts in the slice raise `ParserSeamNotFound` today.

⚠️ **The hoisting hazard is unpaid, not avoided.** `parse_ns` re-executes the script module on every
call. A future run converting 506 sites must hoist into module-level constants or fixtures; this run
converted none, so the hoisted-versus-per-assertion count the done-when asks for is **0 hoisted, 0
per-assertion, 506 unconverted**.

### D4 — Parametrize the tabular cases (**B5**) and strip history from prose (**B3**) — **B3 half done** (commit `8302e17`); **B5 half already satisfied for the named target**

#### B3 — done, 42 → 0

| Measure | Before | After |
|---|---:|---:|
| `test-docstring-historical-prose` (slice) | 42 | **0** |
| `test-docstring-historical-prose` (all of `test/plan-marshall/`) | 43 | **0** |

The done-when reads *"the rule reports zero findings over this slice **or** each remaining finding is
recorded as a data-not-citation case"*. It reports **zero**, so the disjunct's second branch is not
needed.

**The over-stripping risk the plan flags was handled by rewriting, not deleting.** Where a citation
carried the *only* statement of the consequence, the consequence was rewritten in the present tense
and promoted to the subject of the sentence rather than removed with the citation. Examples:

* `manage-architecture/test_cmd_client.py` — "Regression for gemini-code-assist PR #887 finding
  (`'.'.rstrip('/')` is still `'.'`, length 1, which short-circuited step 2)" became the mechanism
  itself: "`'.'.rstrip('/')` is still `'.'` — length 1, not 0 — which short-circuits step 2 unless the
  normalization is explicit." The invariant a maintainer needs survives; only the finding id is gone.
* `build-pyproject/test_dynamic_mypypath.py` — the bare "See lesson-…-mypypath-dynamic" pointer
  carried no rationale at all, so one was written: "A MYPYPATH that stops covering a canonical scripts
  subdirectory makes mypy silently skip those sources."

**Two `TASK-nnn` matches were data, not citations**, and took the rule's literal-span exemption rather
than a rewrite: `plan-doctor/test_plan_doctor.py` names `TASK-001` / `TASK-002` as the **fixture
filenames** the module under test scans. They are now inline literal spans.

One test function was renamed — `test_pr_726_coderabbit_shape` → `test_coderabbit_full_review_shape` —
because the citation was in its *name*. The collected count is unchanged (§ Verification).

#### B5 — the plan's named target was already converged before this run

D4 names "the build-system detection matrices (six implementations × the same contract questions — the
single clearest parametrization target in the slice)". Read before acting on it, **both** cross-directory
contract families already route through one parametrized surface in the shared fixture module:

| Family | State on `main` |
|---|---|
| `coverage-report` | `COVERAGE_REPORT_CASES` + `run_coverage_report_case`, consumed by all four backends through `@pytest.mark.parametrize('case', …)`. npm parametrizes over its own documented subset (`NPM_COVERAGE_REPORT_CASES`) because its report format is Istanbul JSON, and says so |
| `run-config-key` | `assert_run_config_key_contract`, consumed by all four backends, each supplying its own `CANONICAL_ARGS` / `SUFFIX_CASES` table |

Building a second parametrized surface for a contract already parametrized would be the duplication the
deliverable exists to remove. **Not done, because already done** — reported rather than re-built. The
remaining un-parametrized tabular families in the slice (the architecture query filter cases and the
inbox envelope shape cases, both named by D4) are **not** addressed by this run and stay open.

### Condition 4 found a real, pre-existing order-dependent failure — diagnosed and fixed

The plan puts condition 4 there because "D1's consolidation and D3's conversions both change
`sys.modules` registrations, which is the mechanism plan `060` found a live order-dependent failure
in — and which three same-order runs had reported as passing." It fired.

**The symptom.** Forward order: 3,622 passed. Reverse order: **1 failed**, 3,621 passed —
`manage-architecture/test_cmd_resolve.py::test_resolve_coverage_triggers_at_most_one_enrich`.

**Not caused by this run — verified, not argued.** The first question is whether the run introduced
it. Minimal reproducer (two directories, either order), run against **unmodified `origin/main` in a
separate worktree**:

| Ordering | `origin/main` (`eb0124c`) | This branch |
|---|---|---|
| `manage-architecture` before `build-maven` | **1 failed**, 817 passed | **1 failed**, 817 passed |
| `build-maven` before `manage-architecture` | 818 passed | 818 passed |

Identical on both. The defect is pre-existing and latent; the full-slice run in forward order — the
only order anyone had run — passed on `main` and passes here, which is exactly the "three same-order
runs reported as passing" shape.

**The mechanism.** `_cmd_client_query._enrich_maven_module_cached` reaches the seam with a **deferred**
`from _maven_cmd_discover import enrich_maven_module` *inside the function body*, so it resolves the
name through `sys.modules` at **call** time. `test_cmd_resolve.py` patched the module object **it**
loaded at import time. Those are two different objects whenever `build-maven`'s own tests — which load
the same script under the same registration name — are imported last during collection. pytest imports
every collected module before running any test, so which copy owns `sys.modules['_maven_cmd_discover']`
is decided purely by directory order. Collected after `build-maven/`, the patch lands on the reachable
copy and the test passes; collected before it, the patch lands on an unreachable copy, production calls
the **real** `enrich_maven_module`, and the test fails.

**The fix is test-side and inside this slice.** `test_cmd_resolve.py` now patches
`sys.modules['_maven_cmd_discover']` — the object production actually resolves — through a
`_registered_maven_cmd_discover()` helper whose docstring states why the import-time binding is the
wrong target. This is the idiom `manage-architecture/test_native_resolver_graph_impact.py` already uses
for `_cmd_client_query` in the same directory. No `marketplace/bundles/**` file was touched: the
production deferred import is left exactly as it is.

**The fix is proved non-vacuous.** The failing ordering failed *before* the change and passes *after*
it, with the other ordering passing throughout — the defect is the mutation, and the guard discriminates
against it. The test's own assertion is positive (`assert len(enrich_calls) == 1`), not a
`not-in` check, so a patch that reaches nothing leaves the list empty and fails rather than passing
silently. That is precisely how the defect surfaced.

⚠️ **The shape is systemic, and this run closed one instance of it.** After fixing, the tree was swept
for the same shape. The defect needs three things at once: a registration name **used by more than one
test module**, a test that **patches its own import-time binding** of that name, and production that
**resolves the name through a deferred, function-body import**. Measured:

* **25 registration names are used by more than one test module** tree-wide (derived by parsing the
  explicit `module_name` argument of every `load_script_module` call under `test/`).
* **25 module/name pairs patch their own import-time binding** of such a name — the candidate set,
  measured *after* this run's fix, which is why `test_cmd_resolve.py`/`_maven_cmd_discover` is correctly
  absent from it. They span `manage-architecture`, `manage-status`, `plan-orchestrator`,
  `workflow-integration-git`, `workflow-integration-github`, `build-maven`, `tools-integration-ci`,
  `manage-findings` and `plan-retrospective` — so **most are outside this plan's slice**, in
  concurrently-running siblings' directories this plan may not edit.
* The slice's own production scripts (`manage-architecture`, `plan-orchestrator`) carry **13**
  function-body `from _… import …` statements — the third ingredient.

**Only the one instance is confirmed live**, because only it was observed to fail: after the fix the
full slice passes in **both** orders (3,622 each). The remaining 25 candidates are **not** confirmed
defects — each needs its production consumer checked for the deferred-import shape, which this run did
not do. They are recorded in § Residue as a candidate list, deliberately not claimed as defects.

### D5 — Report the measured deltas — **done** (this report)

| Figure | Before | After | Command / population |
|---|---:|---:|---|
| Slice lines | 65,163 | **64,984** | `xargs wc -l` over the Expected-surface list |
| Line delta | — | **−179 (0.275%)** | derived from the two above |
| `.py` files in slice | 180 | 180 | none added, none deleted |
| Collected tests | 3,622 | **3,622** | `pytest --collect-only -q` over the slice |
| Passed / failed | 3,622 / 0 | **3,622 / 0** | `pytest -q -p no:randomly` over the slice |
| **Skipped** | **0** | **0** | same run's summary |
| Wall-clock | 181.20 s | **155.55 s** | same command, same scope, one cloud session. **Faster**, not slower |
| Modules over 400 lines | 63 | **62** | `xargs wc -l \| awk '$1>400'` — reported, not acted on (plan `100` owns it) |
| Coverage of `marketplace/bundles/plan-marshall` | **54%** | **54%** | `pytest {slice} --cov=marketplace/bundles/plan-marshall --cov-report=term`. Before measured on `origin/main` in a **separate worktree**, after on this branch, same command and same scope |
| `Namespace(` | 506 | 506 | B6 half not started |
| `parse_ns(` | 1 | 1 | B6 half not started |

**Doctor `test-conventions`, slice-scoped, per rule:**

| Rule | Before | After |
|---|---:|---:|
| `test-module-line-budget` | 63 | 61 |
| `test-module-preamble-boilerplate` | 47 | **18** |
| `test-docstring-historical-prose` | 42 | **0** |
| `subprocess-pythonpath` | 1 | 1 |
| `unique-fixture-basenames` | 0 | 0 |
| `test-helper-module-misnamed` | 0 | 0 |
| `identifier-validator-corpus` | 0 | 0 |
| **Total** | **153** | **80** |

**On coverage (§ Verification condition 2).** Not merely "does not decrease" — **identical to the
statement**: 24,933 statements, 10,728 missed, 9,392 branches, 963 partial, 54%, on both sides. That is
the expected result for a change that adds no test, deletes no test, and alters no assertion, and it is
reported as a measurement rather than argued from that expectation.

**On the four verification conditions:**

| # | Condition | Verdict |
|---|---|---|
| 1 | Collected test count does not decrease | ✅ 3,622 → 3,622 |
| 2 | Coverage does not decrease | ✅ 54% → 54%, identical to the statement |
| 3 | Skipped count does not rise; suite does not slow down | ✅ 0 → 0 skipped; 181.20 s → 155.55 s (faster) |
| 4 | The slice is order-independent | ✅ **after a fix** — it FAILED first, found a pre-existing defect, and now passes in both orders at 3,622 each |
| 5th (slice-specific) | Daemon-routing neutralization still engages **and discriminates** | ✅ passes as shipped; negative arm fails when the disengaging marker is removed |

**On the line delta.** −0.275% sits inside the epic's measured band (`030`–`060` returned 2.56%,
0.58%, 0.52%, 0.72% against floors of 20–30%). The plan retires its own 20% floor and says the delta
is *reported, not targeted*; this run reports it and chased nothing. No assertion, rationale, or
comment was deleted to move it — the 179 lines are duplicated loader preambles, duplicated
`ExecuteConfig` baselines, and citation text, and the 73-finding drop in doctor findings is the better
measure of what happened.

**The convergence, which is this slice's actual value** (plan § Notes asks for it explicitly):

* **6 of 6** `build-*` directories now stage the extension contract through
  `test/plan-marshall/_build_extension_fixtures.py`, up from 4 of 6 importing it and 0 of 6 sharing the
  `BuildExtension` / `ExecuteConfig` / `sys.path` staging.
* **9 of 9** plan-lifecycle directories: unchanged, because the convergence D2 proposed was already
  present in the three directories that stage a plan directory at all, and the other six stage none.

