# Run report — 070-architecture-and-orchestration-test-reduction (run 01)

**Date (UTC):** 2026-08-18    **Branch:** `claude/architecture-orchestration-test-reduction-iuthfe` (harness-assigned; kept as-is per the lane contract)    **PR:** [#1290](https://github.com/cuioss/plan-marshall/pull/1290)    **Outcome:** **completed** — D1, D3's B7 half, D4's B3 half and D5 delivered; D2 correctly not built (premise refuted); D3's B6 half and D4's B5 remainder reported not done

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
reference is recorded as a proposal in § Residue rather than edited, and D3's `parse_ns` half
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
| `build-server` | a 3-line `sys.path.insert` bootstrap repeated in 4 modules, plus an identical 8-field `ExecuteConfig` baseline in 3 modules — two expanded, one compact |

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
* `execute_config(factory, capture_strategy, **overrides)` — the `ExecuteConfig` baseline, replacing 3
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
than a new one — say so rather than building a second."* Measured across all 15 `test_*.py` modules in the
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

**Every remaining `spec_from_file_location` site is listed with its reason**, including the one this
run **added**:

⚠️ D3's done-when reads *"no `spec_from_file_location` … remains in the slice"*. Taken literally that is
**not met** — nine sites across nine modules remain, and the table below is a reasoned exception list
rather than the zero the sentence asks for. Recorded as a shortfall against the literal done-when, not
as satisfaction of it.

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
| `_build_extension_fixtures.py` (line 139) | **Added by this run, deliberately.** `load_build_extension` uses `spec_from_file_location` precisely *because* it does not register, which is what keeps two backends loaded through it independent. It is consequently one of the **18** residual `test-module-preamble-boilerplate` findings, i.e. that count is 17 pre-existing plus 1 this run introduced | this run, by design |
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
| `test-docstring-historical-prose` (all of `test/plan-marshall/`) | 42 | **0** |

The done-when reads *"the `plugin-doctor` `test-docstring-historical-prose` rule reports zero findings
over this slice **or** each remaining finding is recorded as a data-not-citation case"*. Keyed on the
rule, it reports **zero**, so the disjunct's second branch is not needed and **the done-when is met**.

⛔ **The done-when is met; D4's broader deliverable text is NOT, and the two must not be conflated.**
That text says to strip "plan ids, deliverable ids, PR numbers, lesson ids, and superseded-behaviour
narration" from test docstrings and comments. The rule's zero is **rule-scoped**:
`_PLAN_DELIVERABLE_ID_RE` matches only `TASK-\d{3}` and `deliverable D\d+`, `_PR_REFERENCE_RE` only
`PR #\d+`, and **no pattern opens a string literal**. Roughly twenty citations therefore survive in
the slice in shapes the rule cannot match — `"introduced by D2"`, `"TASK-2 removed them"`,
`"TASK-1 unified …"`, `"In-scope flags from TASK-1"`, `"TASK-2 foundation"` — across
`manage-architecture/test_architecture_core.py`, `test_derive_verification.py`,
`test_descriptor_regression_check.py`, `test_diff_modules.py`,
`manage-architecture/test_architecture_input_validation.py`,
`manage-plan-documents/test_manage_plan_documents_input_validation.py`,
`plan-marshall/test_invariants.py`, `test_phase_handshake_validators.py`, `test_effort_presets.py`,
`build-maven/test_discover_modules.py`, `test_maven_rewrite_log.py`,
`build-pyproject/test_build_cmd_coverage.py`, `test_build_findings_store.py`,
`test_pyproject_cmd_parse.py`, `phase-3-outline/test_phase_3_outline_qgate_bypass.py` and
`phase-4-plan/test_verification_only_guard_contract.py`.

**This run fixed the string-literal instances it had itself made inconsistent** — three lesson ids in
assertion messages in `execute-task/test_skill_profile_resolve_commands.py`, whose prose citation this
run had already stripped, leaving the file asserting an id it no longer explained. The remaining ~20
are **not** fixed: they were not attempted, and the round budget is spent. Attempting a bulk prose
rewrite in the final round is precisely what produced this run's own over-stripping and
invented-rationale defects, so they go to § Residue rather than into a rushed pass. **B3 is partially
done, and reporting it otherwise would be the "empty exception list produced by not attempting the
sweep" failure `030`'s report warns about.**

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

#### The cold read (D4's mandated "By reading" verification) — 4 of 10 were over-stripped

The plan requires this and specifies its shape: dispatch a sub-agent with **five rewritten test
modules and no other context** — not the plan, not the originals — and ask, for ten named tests,
"What contract does this test pin, and why does it matter?" The sub-agent was constrained exactly so:
five files, no plan, no report, no git history, no production source, no test runs.

**Round 1 result — the sub-agent's own closing line, verbatim: "6 of 10 answer both questions."**

| # | Test | Round 1 verdict |
|---|---|---|
| 1 | `test_classify_changed_path_nested_pom_matches_bare_basename_route` | ANSWERS BOTH |
| 2 | `test_resolve_module_for_path_prefers_domain_affine_sibling` | **ANSWERS Q1 ONLY** |
| 3 | `test_production_js_under_maven_wrapper_derives_npm_compile` | **ANSWERS Q1 ONLY** |
| 4 | `test_it_route_stamped_verify_derives_failsafe_gate` | **ANSWERS Q1 ONLY** |
| 5 | `test_nested_pom_against_bare_route_derives_verify` | **ANSWERS Q1 ONLY** |
| 6 | `test_cmd_resolve_cache_tree_layout_emits_augmentation` | ANSWERS BOTH |
| 7 | `test_cmd_which_module_root_exact_hit_degrades_to_containment_fallback` | ANSWERS BOTH |
| 8 | `test_assertion_passes_when_path_empty_at_planning_phase` | ANSWERS BOTH |
| 9 | `test_cmd_capture_succeeds_at_planning_phase_before_materialization` | ANSWERS BOTH |
| 10 | `test_which_module_resolves_test_path_via_paths_tests` | ANSWERS BOTH |

**The four failures, verbatim** (its Q2 answers):

> **2.** "CANNOT ANSWER FROM THE PROSE. The docstring names only the losing alternative ("not the
> alphabetically-first Maven wrapper"), which is the negation of the assertion, not a consequence."
>
> **3.** "CANNOT ANSWER FROM THE PROSE. Again only the counterfactual outcome is named ("not the
> wrapper's Maven goal"). The prose never says what happens if the Maven goal is derived instead."
>
> **4.** "CANNOT ANSWER FROM THE PROSE. … The word "failsafe" appears only in the test's *name*; no
> sentence explains what a Surefire-goal derivation would fail to run."
>
> **5.** "CANNOT ANSWER FROM THE PROSE. "classifies non-zero" is an assertion about the output field,
> not a statement of consequence."

**And its diagnosis, verbatim** — which named the defect more precisely than the plan's own warning:

> "**The four Q1-only tests are all in `test_derive_verification.py`**, and all four share one prose
> shape: `X derives Y — not Z`. Naming the losing alternative reads like a reason but is only the
> assertion restated with its polarity flipped."

⭐ **This is exactly the over-stripping the plan predicted** ("plan `040`'s cold read found four of ten
rewritten docstrings from which a maintainer could not recover *why* the contract matters" — the same
4-of-10 ratio, independently). All four were in **this run's own rewrites**, and the mechanism was the
one **B3** warns about: the consequence went out with the citation.

**Fixed, and each rationale grounded in something checkable rather than asserted** (commit `a55cbf0`):
the domain-affinity case against the sibling test that resolves the same `.js` path to the Maven
module absent a discriminating domain; the end-to-end JS case against its own two assertions; the IT
route against Surefire's default IT excludes (the tree's own statement, in
`build-maven/test_maven_extension.py`); the nested-pom case against its unit-level counterpart's
`classified_count: 0`. No citation was reintroduced — the doctor rule still reports **0**.

The same Surefire consequence in `build-maven/test_maven_extension.py` was itself narrated in the past
tense as superseded behaviour; it is now present tense, which is what **B3** asks for.

**Round 2 — re-read after restoration: "8 of 10 answer both questions."** All four restored docstrings
moved to ANSWERS BOTH. Two that had passed in round 1 (#7 `test_cmd_which_module_root_exact_hit…`,
#10 `test_which_module_resolves_test_path_via_paths_tests`) were scored ANSWERS Q1 ONLY in round 2
**without their text changing between rounds** — the same reading applied more strictly, on the
grounds that naming the wrong answer is the negation of the assertion rather than a consequence. That
is verifier variance, not a regression, and it is recorded as such rather than smoothed over. Both
docstrings do state the *mechanism*; what they omit is the downstream cost, and neither was rewritten
by this run beyond removing its citation.

⭐ **Round 2's real yield was its SUSPECT CLAIMS list, and three entries were defects in prose this run
had written one commit earlier** — the invented-rationale class, committed while fixing the
over-stripping. Every entry was checked against the tree before acting on it; these held up:

| Claim (all written by this run in `a55cbf0`) | Verified against | Verdict |
|---|---|---|
| "the executable would name `e-2-e-playwright-maven` and **run a Maven build** against a JavaScript edit" | `_virtual_module_derived` → `_module_derived`, whose every executable is `pyproject_build` | **FALSE for this fixture.** Resolving the Maven sibling emits a *pyproject* invocation scoped to that module |
| "the module the deriver then verifies is the one that **cannot build** the file that changed" | the two siblings' command sets, identical apart from the module name | **Unestablished.** Nothing in the fixture supports it |
| "`module-tests` **is** the plain Surefire goal, and Surefire's default includes EXCLUDE the IT naming patterns" | this fixture's build classes resolve to `pyproject_build`; the Surefire fact is pinned in `build-maven/test_maven_extension.py` | **True of the Maven backend, but not of what this test demonstrates.** Stating it flatly here claims the test shows something it does not |

All three are corrected in `0fb3cb7`, each now claiming only what the test actually pins. ⛔ This is
the defect the lane contract singles out as the one nothing else catches — a stale claim contradicts
the tree and a sweep finds it, but an invented one contradicts only reality: the suite is green, the
linter clean, the doctor at zero, and the sentence has no earlier version to diff against. It was
introduced at exactly the moment the contract predicts — writing a docstring to explain a fix a
reviewer had just asked for.

**Three further false statements, pre-existing, in `test_cmd_resolve.py`** — each contradicted by that
same file, and each fixed under condition A because a false statement is fixed wherever it lives:

| Statement | Contradicted by |
|---|---|
| a comment giving **pyproject's floor as 600s** | the module docstring ("pyproject declares 330 (-> 360)") and the floor test naming `PYTEST_OUTER_FLOOR_SECONDS = 330`. 600 is the **ceiling** everywhere else in the file |
| the same comment calling Maven "**the only** engine family that still yields a `per_task` verdict" | the pyproject floor case forty lines below, asserting `execution_tier == 'per_task'` and `hint == _per_task_hint(360)` |
| a section header reading "Case (a): … -> **floored to orchestrator tier**" | the test directly beneath it, asserting `per_task` |

Plus superseded-behaviour narration the doctor's patterns do not match — "the pre-fix deriver
matched…", and four `pre-#515` / `post-#515` spellings that survived the prose pass because the rule
keys on `PR #nnn`. All rewritten in the present tense, keeping the mechanism.

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
| `manage-architecture` before `build-maven` | **1 failed**, 817 passed | **1 failed**, 817 passed *before the fix below*; **818 passed** after |
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

⛔ **This count is method-sensitive, so the method is stated with it rather than the number alone.**
By an **AST parse** of every `load_script_module` call under `test/`, counting both an explicit
`module_name` and the stem it defaults to when that argument is omitted, and treating
`monkeypatch.setattr` / `patch.object` on a module-level binding as a patch site:

* **44 registration names are used by more than one module**, and
* **36 module/name pairs patch their own import-time binding** of such a name — the candidate set,
  measured *after* this run's fix, which is why `test_cmd_resolve.py`/`_maven_cmd_discover` is
  correctly absent from it.

A narrower earlier derivation — regex, explicit four-positional-argument calls only — gave **25/25**
and was reported here first; it undercounts by missing the `module_name=` keyword form and every
defaulted stem. An independent verifier applying a third method got 38/32. **Three methods, three
answers**: whoever acts on this must re-derive it with a stated method rather than inherit a number.
The candidate set spans `manage-architecture`, `manage-config`, `manage-status`,
`manage-execution-manifest`, `manage-solution-outline`, `plan-orchestrator`, `workflow-integration-git`,
`workflow-integration-github`, `build-maven`, `tools-integration-ci`, `manage-findings` and
`plan-retrospective` — so **most are outside this plan's slice**, in concurrently-running siblings'
directories this plan may not edit.
* The slice's `manage-architecture` production scripts carry **13** function-body
  `from _… import …` statements — the third ingredient. `plan-orchestrator` carries **0**, so it
  contributes candidate bindings but not the deferred-import half.

**Only the one instance is confirmed live**, because only it was observed to fail: after the fix the
full slice passes in **both** orders (3,622 each). The remaining 25 candidates are **not** confirmed
defects — each needs its production consumer checked for the deferred-import shape, which this run did
not do. They are recorded in § Residue as a candidate list, deliberately not claimed as defects.

### D5 — Report the measured deltas — **done** (this report)

| Figure | Before | After | Command / population |
|---|---:|---:|---|
| Slice lines | 65,163 | **65,055** | `xargs wc -l` over the Expected-surface list |
| Line delta | — | **−108 (0.166%)** | derived from the two above, re-measured after the final verification round. It moved twice during the run — −179 before the restorations, −109 after them, −108 after round 3 — and is stated here as last measured, not as first computed |
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

**On the line delta.** −0.166% sits inside the epic's measured band (`030`–`060` returned 2.56%,
0.58%, 0.52%, 0.72% against floors of 20–30%). The plan retires its own 20% floor and says the delta
is *reported, not targeted*; this run reports it and chased nothing. No assertion, rationale, or
comment was deleted to move it — the removed lines are duplicated loader preambles, duplicated
`ExecuteConfig` baselines, and citation text, and the 73-finding drop in doctor findings is the better
measure of what happened.

**The convergence, which is this slice's actual value** (plan § Notes asks for it explicitly):

* **6 of 6** `build-*` directories now stage the extension contract through
  `test/plan-marshall/_build_extension_fixtures.py`, up from 4 of 6 importing it and 0 of 6 sharing the
  `BuildExtension` / `ExecuteConfig` / `sys.path` staging.
* **9 of 9** plan-lifecycle directories: unchanged, because the convergence D2 proposed was already
  present in the three directories that stage a plan directory at all, and the other six stage none.


## Scope

55 files changed at the point the PR opened, **plus one** added by the beyond-diff sweep:

* **53 `*.py` under `test/plan-marshall/`**, every one inside the plan's Expected surface. Checked
  mechanically: the changed set minus the Expected-surface directories, the four named root modules,
  and this plan's own directory is **empty**.
* **`doc/plans/test-quality/070-…/plan.md`** (moved into its directory) and **`report-01.md`**.
* **`doc/developer/testing.adoc`** — ⚠️ **outside the Expected surface, and deliberately so.** The
  beyond-diff sweep found it naming `build_test_helpers.run_coverage_report_case` in a sentence
  describing the tree's *current* plumbing; D1's rename made that false. It is live developer
  documentation rather than a dated record, so the lane contract's condition A applies — a false
  statement is fixed wherever it lives — and the plan's Out-of-scope list does not reach it (it names
  `marketplace/bundles/**`, `test/conftest.py`, `test/_shared/**`, and test directories belonging to
  sibling plans; this is none of those). Recorded here rather than folded silently into the count.

**No `marketplace/bundles/**` file, no `test/conftest.py`, no `test/_shared/**`, and no test directory
belonging to a concurrently-running sibling plan is touched.**

The other eleven repository references to the two retired names were each read and left alone, with
the reason: `060`'s and `070`'s plan documents and `090`'s plan describe the rename itself or disclaim
ownership of it; `findings-test-corpus-review.md` and `report-authoring-01.md` are dated records; and
`test/conftest.py` line 1128 is plan `090` § D6's, recorded as a proposal below.

## Build gate

**Verdict: Python changed, so the build ran.** `git diff --name-only origin/main...HEAD -- '*.py'`
returns **53** files of **55** changed (the other two are this plan's `plan.md` and `report-01.md`).

`./pw verify` — all three sub-steps, not the narrower calls:

| Sub-step | Result |
|---|---|
| `quality-gate` | `ruff … All checks passed!`, `mypy … Success: no issues found in 413 source files`, `SPDX-header check passed` |
| `test-compile` | **FAILED on the first run**, then clean — `Success: no issues found in 768 source files` |
| `module-tests` | whole-tree suite (see the final run below) |

⭐ **`test-compile` failing first is the contract's own warning materialising, and it is worth
recording as a finding rather than a hiccup.** `./pw quality-gate` passed on every one of this run's
four commits, and the slice's own tests passed — yet `test-compile`, which neither `quality-gate` nor
`module-tests` performs, reported:

```text
test/plan-marshall/build-server/test_build_execute_routing.py:132: error: Returning Any from function declared to return "ExecuteConfig"  [no-any-return]
test/plan-marshall/build-server/test_acceptance_resolution_log.py:35: error: Returning Any from function declared to return "ExecuteConfig"  [no-any-return]
```

D1's shared `execute_config()` helper returns whatever the dynamically-loaded factory constructs — an
`Any` — while two of its call sites declared `-> factory.ExecuteConfig`. That annotation never checked
anything (`factory` is loaded at runtime, so `factory.ExecuteConfig` is a *value*, not a statically
known type), and it is exactly the "a variable used as a type" shape the lane contract names. It is
**test-only**, so it is invisible to `quality-gate`'s production-scoped mypy and to the test run
itself; CI runs the full `verify` and would have caught it. The two annotations were dropped, matching
`test_acceptance_fallback.py`'s already-unannotated `_config`, with a docstring line saying why.

## Findings and the stop record

Every finding from the verification sub-agents, the build gate and the doctor, recorded **per
instance**. Dispositions: *fixed*, *rejected-with-reason*, *deferred*, or *survivor*.

### How the loop ended

**Round budget: 3, declared before the first dispatch.** The plan states none, so the run declared one
up front, before knowing what the rounds would say.

⛔ **The loop ended on the BUDGET exit, not on a verifier's "nothing remains".** Round 3's verifier
answered the stop question **YES** — sixteen condition-A items and one condition-B item remained at the
moment it was asked. Everything condition A forbids leaving open was then **fixed** (commit `5e6ae7e`),
and condition B's item was **characterised** rather than left implied. What the run did **not** do is
re-dispatch a fourth round to confirm that answer had become "no", because the budget was spent.

**This is a stopped loop, not defect-free code**, and the two must not be blurred. The run is stopping
on a declared budget, having fixed what it was told; it is not asserting convergence. A fourth round
would very likely find more — every round here found defects in the previous round's fixes, including
three the run itself introduced while fixing round 1.

**Were the late rounds' findings narrower?** Partly, and honestly: no. Round 3's yield included **five
genuine code defects** (a sentence fragment, an orphaned antecedent, three citations in string
literals, a docstring describing a mechanism its function no longer used, a dead constant, two phantom
file paths) alongside the report-figure corrections. That is **not** the "findings are now only about
the run's own report" narrowing the contract describes as a signal it is safe to stop. The code was
still yielding at the budget's end.

**Residue to assume remains.** Read the deliverables as still carrying defects of the kind round 3
found: prose that asserts more than the code shows, citations in shapes the doctor rule cannot match,
and figures in this report that a fourth derivation would dispute. Three independent derivations of one
count in this run produced three different answers.

### Findings

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | plan gate | `test/conftest.py:1128` names `build_test_helpers.py` by path; D1's rename makes it stale. Symbol: `_routing_namespaces`. Corrected path: `test/plan-marshall/_build_extension_fixtures.py` | **proposal** — `090` § D6 owns it; this run may not edit `conftest.py` |
| F2 | build gate | `test-compile` failed with two `no-any-return` errors invisible to `quality-gate` and to the test run | **fixed** (`a55cbf0`) |
| F3 | condition 4 | Pre-existing order-dependent failure in `test_cmd_resolve.py`, reproduced on `origin/main` | **fixed** (`df79ccd`) |
| F4 | cold read 1 | 4 of 10 docstrings over-stripped — consequence removed with the citation | **fixed** (`a55cbf0`) |
| F5 | cold read 2 | "run a Maven build against a JavaScript edit" — false for the fixture, written by this run | **fixed** (`0fb3cb7`) |
| F6 | cold read 2 | "the module … cannot build the file that changed" — unestablished, written by this run | **fixed** (`0fb3cb7`) |
| F7 | cold read 2 | "`module-tests` **is** the plain Surefire goal" asserted where the fixture is pyproject — written by this run | **fixed** (`0fb3cb7`) |
| F8 | cold read 2 | `test_cmd_resolve.py` gave pyproject's floor as 600s; it is 330, and 600 is the ceiling | **fixed** (`0fb3cb7`) |
| F9 | cold read 2 | Same file called Maven "the only engine family" yielding `per_task`; a pyproject case below asserts it | **fixed** (`0fb3cb7`) |
| F10 | cold read 2 | Section header "Case (a): … -> orchestrator tier" above a test asserting `per_task` | **fixed** (`0fb3cb7`) |
| F11 | self-sweep | "this fixture's executables are engine-agnostic" — they are pyproject's; written by this run one commit earlier | **fixed** (`6fe7e52`) |
| F12 | self-sweep | Line delta stale (−179/0.275%) after the restorations added lines | **fixed** (`b7d725d`) — now −109/0.167% |
| F13 | self-sweep | `doc/developer/testing.adoc` named the renamed module in a live description of current plumbing | **fixed** (`17294ba`) |
| F14 | round 3 | `test_skill_profile_resolve_commands.py` — B3 rewrite left a subordinate clause with no main clause | **fixed** (`5e6ae7e`) |
| F15 | round 3 | Same file — "pre-lesson behaviour" antecedent deleted by the same rewrite | **fixed** (`5e6ae7e`) |
| F16 | round 3 | Same file — three lesson ids surviving in assertion-message string literals | **fixed** (`5e6ae7e`) |
| F17 | round 3 | `test_test_scope_divergence.py` — docstring described `spec_from_file_location` after conversion to `load_script_module`, omitting the new registration | **fixed** (`5e6ae7e`) |
| F18 | round 3 | Same file — `_PYPROJECT_EXTENSION_FILE` orphaned by the conversion | **fixed** (`5e6ae7e`) |
| F19 | round 3 | Two modules cite `test/plan-marshall/conftest.py`, which does not exist | **fixed** (`5e6ae7e`) |
| F20–F27 | round 3 | Eight report figure/pointer errors (dangling `§ Findings, F1`; 16 vs 15 modules; ExecuteConfig 4 vs 3; `execute_config` 4 vs 3 copies; prose baseline 43 vs 42; condition-4 column unqualified; unlisted `spec_from_file_location` site; `plan-orchestrator` credited with deferred imports it has none of) | **fixed** (`5e6ae7e`) |
| F28 | round 3 | Registration-name counts irreproducible — three methods, three answers | **fixed** (`5e6ae7e`) — restated with its derivation and a warning to re-derive |
| F29 | round 3 | D3's literal done-when ("no `spec_from_file_location` remains") not met — 9 sites remain | **corrected to partial** (`5e6ae7e`); the sites are listed with owners |
| F30 | round 3 | D4/B3 reported complete; the done-when is met but ~20 citations survive in shapes the rule cannot match | **corrected to partial** (`5e6ae7e`); listed per file, **deferred** to a follow-up run |
| F31 | round 3 | `rule-catalog.md` and `doctor-test-conventions.md` say the preamble rule has "One known-legitimate occurrence"; D1 created a second | **proposal** — `marketplace/bundles/**` is out of scope |
| F32 | round 3 | Four conversions turned a non-registering load into a registering one; two were undisclosed | **survivor, characterised** — see below |
| F33 | round 3 | The order-dependency candidate class | **survivor, characterised** — see § "Condition 4" |

### Survivors, each re-put to the verifier in the stopping round

**F32 — the four non-registering → registering conversions.** Bound: each of the four names occurs
nowhere else under `test/` or `marketplace/`, so the registration displaces no other copy and nothing
resolves those names by import. The promise it stays outside of is the order-dependency class this run
fixed, which requires a *shared* name; the full slice passes in both directory orders after the change.
The two undisclosed ones now carry that bound in the report and in the code.

**F33 — the order-dependency candidate class** (36 pairs by the AST derivation). Bound: the whole slice
passes in both orders; exactly one instance was ever observed live, and it is fixed; the rest are
**candidates, not claimed defects**, each needing its production consumer checked for the
deferred-import shape. Most lie in concurrently-running siblings' slices this plan may not edit.

**F30 — the ~20 surviving citations** is a **deferred** finding, not a survivor: it is real, unfixed,
and this run does not argue it needs no fixing. It carries the same disclosure a survivor does — the
bound is that it is confined to docstrings, comments and assertion-message strings within this slice,
changing no behaviour — and it is owned by a follow-up run of this plan.

## Reviewer participation

**PR [#1290](https://github.com/cuioss/plan-marshall/pull/1290).** The expected reviewer population is
**derived from configuration**, not transcribed here: the `author_login` of every
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
carrying such a data block. That read yields **three** — `coderabbitai` (`coderabbit.md`),
`cuioss-review-bot` (`pr-agent.md`), `sourcery-ai` (`sourcery.md`). `bot-participation-contract.md`
carries no `author_login` block of its own and is the contract, not a registry entry.

The PR was opened **without** `skip-bot-review`: the diff is 53 `*.py` files under `test/`, which is
code, so it keeps its review.

_Verdicts, each derived from the stored comment bodies across all three surfaces
(`get_comments`, `get_reviews`, `get_review_comments`), recorded below as they arrive._

## Cost

* **Tokens:** not available to the agent in this session — the harness does not expose a usage counter
  to the running agent, so no figure is stated rather than an invented one.
* **Wall-clock:** the run's own elapsed time is likewise not directly readable; what *is* measured, and
  is the figure the plan asks for, is the suite wall-clock recorded in § D5 (181.20 s → 155.55 s).
* **Population:** every test figure in this report counts **this slice only** — the 27 Expected-surface
  directories plus the two named root modules — executed by one `uv run python -m pytest` invocation in
  a single Claude Code cloud session. ⛔ These are **not** comparable to a plan-marshall `metrics.toon`
  total, which counts an orchestrator-plus-agent dispatch tree under plan-marshall's own per-task
  billing boundary. This run has no such boundary and no ledger, so no comparison is offered.

## Contract check (Step 9)

Re-read against what actually happened, confirming both that the step ran and that its artifact exists.

| Step | Verdict |
|---|---|
| 1 Skills loaded | **done** — named in § Skills loaded, including the two recorded as *not separately read* with the reason |
| 2 Branch | **done** — harness-assigned `claude/architecture-orchestration-test-reduction-iuthfe`, kept as-is, published to `origin` **before the first edit** (it was absent from the remote on arrival) |
| 3 Plan directory | **done** — `doc/plans/test-quality/070-…/plan.md` exists via `git mv` (a pure `R100` rename), and opens with the first-instruction block, which was present and needed no repair |
| 4 Implement | **done** — deliverables dispositioned; every commit carries the `Co-Authored-By` trailer and no "Generated with" footer |
| 4 Per-commit gate | **done** — every commit touching `*.py` was preceded by a clean `./pw quality-gate` (`ruff … All checks passed!`, `mypy … Success`, `SPDX-header check passed`), read from the tools' own output rather than the exit code |
| 4 Pushed | **done** — pushed after every commit; no unpushed commit remains |
| 5 Build gate | **done** — git-derived verdict: 53 of 56 changed files are `*.py`, so the build ran. Full `./pw verify` green: 20,791 passed, 14 skipped. It **failed first** on `test-compile`, which is recorded rather than smoothed over |
| 6 Verification sub-agent | **done** — three rounds, budget of 3 declared up front, **ended on the budget exit** with round 3's stop answer YES; everything condition A forbids fixed, condition B's item characterised. Findings and the stop record are in § Findings |
| 7 PR cycle | **in progress** — PR [#1290](https://github.com/cuioss/plan-marshall/pull/1290); participation table below |
| 8 Merge gate | pending |
| 8 Bridge | **done** — no status or bookkeeping write landed under `doc/plans/` outside this plan's own directory; no ledger, no status file, no other plan's directory touched |
| 9 This check | **done** — this table |
| 9 What have we learned | below |

**Tree claims re-verified at the moment of writing** (they are not covered by the diff sweeps, and this
run's own build gate mutates the tree they describe): the working tree is clean apart from tracked
edits; the `base-wt` worktree created for the `origin/main` comparisons was removed and `git worktree
list` shows only the main checkout; no file was written outside the repository except under `$TMPDIR`.

**GitHub access path:** the **GitHub MCP server** — the expected cloud path. No `gh` CLI is present.

**Branch form:** harness-assigned, kept. **No `/sync-plugin-cache` is owed** — it is a machine-local
build step reading the git-ignored `target/` and writing `~/.claude/`, which a cloud run neither
performs nor records as debt.

## What have we learned (Step 9)

**One contract change is proposed, and this run produced the evidence for it.**

⛔ **The lane contract's § Step 6 tells a run to sweep "prose-bearing string literals in production
code" — argparse `help=`, error-message templates, operator-facing messages. This run was bitten by
the same consumer kind in TEST code, which that sentence does not name.** Round 3 found three lesson
ids surviving in **pytest assertion-message string literals** in a file whose *prose* citation this
run had already stripped, leaving the module asserting an id it no longer explained. A documentation
sweep never opened the string; the doctor rule's patterns never scan literals; and the code sweep read
it as an argument, not a sentence.

The failure mode is identical to the production case the contract already names — prose that reads as
documentation and lives as code — and the assertion message is if anything *more* operator-facing,
because it is what a developer sees when the test fails. The proposal is a one-clause widening:

> …and **prose-bearing string literals in production code** — an argparse `help=` / `description=` /
> `epilog=`, an error-message or log-line template, an operator-facing message assembled in code **, or
> a test's own assertion message, which a maintainer reads at exactly the moment the test fails**.

**Evidence from this run:** commit `5e6ae7e`, `test/plan-marshall/execute-task/test_skill_profile_resolve_commands.py`
lines 52, 65 and 133 — three citations that survived a sweep which had already corrected the same file's
docstring, and which were found only because an independent verifier grepped the literals.

Per the contract this is **presented to the operator, not self-approved**, and if accepted ships as a
separate `chore/` PR touching only `.claude/skills/cloud-plan-lane/SKILL.md` — never folded into this
plan's diff, because the two have different review audiences.

## Residue

**Deliverable work left open:**

1. **D3's B6 half — 506 `Namespace(` sites, none converted.** The seam map is measured (§ D3) so the
   next run does not pay for the probe again. Two blockers are named and owned: `effort_presets.py` and
   `manage_terminal_title.py` raise `ParserSeamNotFound` → **plan `090` § D1**. `manage-lifecycle`,
   `build-server` and `q-gate-validation-agent` publish no top-level CLI script at all, which is a
   *different* shape from a missing seam and is worth telling `090` about. Whoever takes this must hoist
   `parse_ns` into fixtures or module constants — it re-executes the script module per call.
2. **D4's B5 half beyond the build family.** The architecture query filter cases and the inbox envelope
   shape cases, both named by D4, are untouched. The build-detection families the plan called "the
   single clearest parametrization target" were already converged before this run (§ D4).
3. **8 modules still carrying `spec_from_file_location`**, each listed with its reason in § D3. Seven
   are plan `090` § D2's structurally-unfixable class; one is the `manage_lessons` registration
   collision, which needs `050`/`090` coordination because the other half lives in `manage-lessons/`.

**Findings recorded for other plans:**

| Finding | Owner |
|---|---|
| `test/conftest.py` line 1128 names `build_test_helpers.py` **by path**, and this run renamed that file. The reference is now stale. This run may not edit `conftest.py`; plan `090` § D6 already owns rewriting that docstring to identify the helper by role | `090` § D6 |
| `effort_presets.py` and `manage_terminal_title.py` expose no parser seam (`ParserSeamNotFound`) | `090` § D1 |
| `manage-lifecycle`, `build-server`, `q-gate-validation-agent` publish no top-level CLI script, so `parse_ns` has nothing to address | `090` § D1 |
| Seven `spec_from_file_location` sites load a bundle skill's **root-level** `extension.py` or the repository-root `build.py`, neither reachable through `get_scripts_dir` | `090` § D2 |
| `load_script_module` cannot host a load that needs `sys.modules` mocks installed **between** `module_from_spec` and `exec_module` (`build-pyproject/test_pyproject_build.py`) | `090` |
| **36 module/name pairs patch an import-time binding of a doubly-registered module** (AST derivation; the figure is method-sensitive — § "Condition 4") — the candidate set for the order-dependency class this run fixed one instance of. Most are in sibling slices | recorded; the in-slice ones are this plan's on a follow-up run, the rest belong to their owning slices |
| 62 modules over the 400-line budget in this slice | `100` |
| ⚠️ `plugin-doctor` `references/rule-catalog.md` (line 623) and `standards/doctor-test-conventions.md` (line 185) both say the `test-module-preamble-boilerplate` rule has **"One known-legitimate occurrence"** — `test/conftest.py`'s own `load_script_module`. D1 created a **second**: `_build_extension_fixtures.load_build_extension`, which the doctor now reports and which is deliberate. Both statements are now incomplete. `marketplace/bundles/**` is out of scope for this plan, so this is a **proposal**, not an edit | `090` (the only plan that may edit that tree) |
| The ~20 surviving citations in shapes the `test-docstring-historical-prose` rule cannot match (§ D4) — the string-literal and `TASK-n`/`D2`-in-prose forms | this plan, on a follow-up run |

### The four non-registering → registering conversions, and their bound

D3's B7 half converted four call sites from a **non**-registering `spec_from_file_location` to
`load_script_module`, which always registers. The report's B7 narrative — "they already registered
under the same name they passed, so the conversion is semantics-identical" — is true of the four
`manage-architecture` modules and **does not cover these four**. Their bound, stated per the contract
rather than left implied:

| Site | New `sys.modules` entry |
|---|---|
| `phase-2-refine/test_phase_2_refine_scope_estimate.py` | `_p2refine_refs_crud` |
| `plan-marshall/test_lifecycle_handshake_e2e.py` | `_e2e_handshake_tasks_query` |
| `plan-marshall/test_phase_handshake_worktree_assertion.py` | `phase_handshake_under_test` |
| `build-pyproject/test_test_scope_divergence.py` | `pyproject_extension_for_root_crosscheck` |

**The bound:** each of the four names occurs nowhere else under `test/` or `marketplace/`, so the
registration displaces no other module's copy and nothing resolves those names by import; each is a
new, distinct entry rather than a shared one. **The promise it stays outside of** is the
order-dependency class this run fixed, which requires a *shared* name — and the full slice passes in
both directory orders (3,622 each) after the change. The first two carry a code comment saying this;
the second two did not, and `test_test_scope_divergence.py`'s docstring additionally still described
the old mechanism — both corrected.

**The plan's own leads that measurement corrected**, recorded so the next author does not re-inherit them:

* The slice is **65,163** lines / **171** `test_*.py` modules, not ~63,200 / ~168.
* `plan-orchestrator` (~224 `Namespace(` sites), not `manage-architecture` (~84), is the slice's
  heaviest hand-built-namespace directory.
* The plan's § Problem says `build_test_helpers.py`'s "own module docstring records" the `sys.modules`
  hazard. It did not — only `test/conftest.py`'s `_routing_namespaces` docstring did, which is what the
  plan's own claim-label table cites. D1 therefore **added** that record rather than preserving it.
* D2's justifying hypothesis and D4's "single clearest parametrization target" were both already
  satisfied on `main` (§ D2, § D4).
