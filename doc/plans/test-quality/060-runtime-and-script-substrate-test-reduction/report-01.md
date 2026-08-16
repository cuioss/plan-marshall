# Run report — 060-runtime-and-script-substrate-test-reduction (run 01)

**Date (UTC):** 2026-08-16    **Branch:** `claude/runtime-script-substrate-tests-qqeuoj`    **PR:** _(pending)_    **Outcome:** partial

The slice's house-style deliverables (D1, D3, D4, D5) landed and are measured below. **D2 did not
land**, and the plan's 25% line floor was not reached — by a wide margin. Both are stated in full at
§ Verification and § Residue rather than softened here.

**Population note, because every figure below depends on it.** This run's working surface is **15
directories** — the plan's fourteen plus `test/pm-code-intelligence/`, claimed by operator decision
(§ Gating checks). Unless a row says otherwise, every figure counts the **15-directory** population:
**118 modules**. Where a figure is quoted over the plan's own fourteen it is labelled `14-dir`.
`test/pm-code-intelligence/` contributes 1 module, 260 lines, 3 `monkeypatch` isolation calls and 0
fixtures, so the two populations differ slightly and the difference is stated rather than blurred.

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `.claude/skills/cloud-plan-lane/SKILL.md` — loaded as the first action |
| `plan-marshall:ref-code-quality` | read at `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md` |
| `pm-plugin-development:plugin-script-architecture` | read at its bundle path |
| `pm-dev-python:pytest-testing` | read at its bundle path (Python tests are the whole surface) |
| `plan-marshall:persona-module-tester` | read for the landed module budget (400 lines) |

The `plan-marshall` plugin is not installed in this cloud session, so every skill was read by bundle
path, which is the route the lane names as always available here.

## Gating checks (run before D1, as the plan requires)

| Gate | Result |
|---|---|
| Plans `010` and `020` landed | **PASS** — `parse_ns` at `test/conftest.py:569`; the 400-line module budget at `persona-module-tester/standards/testing-methodology.md:75` |
| No property-based test exists tree-wide | **CONFIRMED** — `grep -rn 'hypothesis\|@given\|strategies' test --include=*.py` returns 3 hits, all incidental (a `test_strategies_are_distinct_objects` about re-review strategy objects, a docstring reading "capture strategies", the word "hypothesised"). No Hypothesis import, no `@given`. D5's table starts from zero, per the plan's fallback |
| The partition holds | **FAILS — one genuine defect, see below** |

### Partition defect (halting gate — escalated, operator overrode)

The derivation covered every directory under `test/plan-marshall/*/`, every file at the root of
`test/plan-marshall/`, and every top-level `test/` entry other than `plan-marshall/`, against the
Expected-surface list of all six plans `030`–`080`. **0 entries were double-claimed.** Three were
claimed by no plan:

| Entry | Verdict |
|---|---|
| `test/README.md` | **Not a defect** — plan `020`'s D4 deliverable, named in `020`'s own Expected surface. Same category as the README's three declared exclusions, which are also `020`'s; the exclusion list simply predates it |
| `test/test_shared_harness.py` | **Not a defect** — plan `020`'s D5 deliverable, likewise named in `020`'s Expected surface |
| `test/pm-code-intelligence/` | **GENUINE DEFECT** — 1 module, 260 lines, claimed by no plan and named nowhere in the epic. Added by PR #1243 (`c86de8b`) **after** the epic was authored by PR #1240 (`c5144e7`) — exactly the "directory added between authoring and a run" case `doc/plans/test-quality/README.md` warns "would be silently skipped, with nothing positioned to notice" |

The plan labels this gate *"gating and halting"* and forbids claiming or skipping the entry
unilaterally. The operator was reachable, so the decision was escalated via `AskUserQuestion`.

**Question asked:** whether to (a) record the defect and execute plan 060's own cleanly-claimed slice,
(b) halt entirely, or (c) claim the directory into this plan and refactor it. Option (c) was presented
as **not recommended**, with the reason stated: the plan and the epic README both forbid claiming an
unclaimed entry unilaterally, and a concurrent sibling may later claim it.

**Operator answer:** *"Add it to 060's slice and refactor it"* — option (c).

Recorded here as an **operator-authorised deviation** from the plan's stated constraint. The working
surface is therefore 15 directories.

**The claimed directory was NOT brought up to the plan's standard, and that is a gap, not a no-op.**
An earlier draft of this report said the directory "needed no change under any deliverable". That was
wrong. `test/pm-code-intelligence/plan-marshall-plugin/test_lsp_derivation_resolver.py:27` carries an
open `test-module-preamble-boilerplate` finding — a hand-rolled `spec_from_file_location` squarely
within **D3**. The file is verified absent from the diff, so the claim altered no file; but it needed a
D3 change and did not get one. It is carried at § Residue.

## Deliverables

| # | Deliverable | State | Commits |
|---|---|---|---|
| D1 | Hoist repeated isolation setup into fixtures | **done** | `8d924e3`, + follow-up |
| D2 | Split every module over the budget | **NOT DONE** | — |
| D3 | Normalise preambles and argument construction | **partial** | `a8bc055`, + follow-up |
| D4 | Parametrize tabular cases; strip history from prose | **partial** (prose half complete) | `48d8c30`, `21e46cb` |
| D5 | Derive the property-based-testing candidate list | **done** (report deliverable) | this report |
| D6 | Report the measured deltas | **done** | this report |

### D1 — isolation setup hoisted into fixtures — **done**

**289 inline isolation statements were removed from test bodies and re-expressed as 47 fixtures**,
each **explicitly requested by name**. (289 = 278 in the first pass + 11 in the follow-up. 47 = 48
created − 1 removed as a duplicate; `@pytest.fixture` count over the slice moved 37 → 84.) Every
number here is a count of *statements and fixtures*, not of diff lines — an earlier draft quoted 278
as "call sites" when it was the tool's rewrite count, and the two are not the same measure.

Candidates were selected mechanically: an isolation call repeated in ≥3 tests of one class or module,
**and** whose free names all bind at module level. 46 of the 83 raw repetition groups met that bar on
the first pass.

**The plan's worked case is included:** `test_claude_runtime.py::TestReadActiveOrchestrator` and three
classes of `test__claude_runtime_impl.py` no longer repeat the `_SESSION_CACHE_BASE` redirect per test.

**Ratio before/after, as the deliverable requires** — stated over both populations, since the plan's
own metric is defined over its fourteen:

| Population | before | after |
|---|---|---|
| 15-dir (this run's surface) | 655 / 37 = **17.70 : 1** | 536 / 84 = **6.38 : 1** |
| 14-dir (the plan's own) | 652 / 37 = **17.62 : 1** | 533 / 84 = **6.35 : 1** |

(`monkeypatch.setattr` + `monkeypatch.setenv` over `@pytest.fixture`, counted per file.)

**Three further groups were re-examined and hoisted after review.** An earlier draft characterised all
37 residual groups as "genuine per-test needs, not missing fixtures". That was overstated: for three of
them the only thing making the call test-local was a **function-local import**, which a fixture can
perform itself. Two were converted (`TestReadTitleState` ×7 and `TestResolveArchivedStatusJson` ×4 of
`monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")`, now a `plan_dir_name` fixture that does its own
`import claude_runtime as _cr`). The third — `TestSessionRenderTitleSessionTitleEmit`'s ×3 `sys.stdin`
redirect — is a genuine missing fixture too and is carried at § Residue, not reclassified.

**One candidate group was deliberately rejected** — Findings F1.

**By reading, as the plan's Verification requires.** Every fixture D1 introduced was re-read from its
own definition. All are `@pytest.fixture()` with **no `autouse=True`** and **no non-default `scope`** —
function-scoped, which is the narrowest scope available to them, because each composes `tmp_path`
and/or `monkeypatch`, both function-scoped by pytest's own definition. A broader scope is therefore not
merely unnecessary but unavailable. Every class-level fixture takes `self`. (The slice contains 13
`autouse=True` fixtures; all 13 pre-date this run.) **No scope errors are left in place**, so the
plan's "report any you leave in place and why" has an empty answer, and this sentence is what makes
that emptiness legible.

### D2 — split every module over the budget — **NOT DONE**

**No module was split. 53 of 118 modules remain over the 400-line budget**, from
`platform-runtime/test_claude_runtime.py` at 4,668 lines down to
`script-shared/test_warnings_classify.py` at 406.

The count moved 55 → 53. **Neither drop came from a split.** `extension-api/test_configurable_contract.py`
fell 589 → 390 as a side effect of **D4's parametrization**, and
`tools-input-validation/test_lesson_id_scanner.py` fell below 400 as a side effect of **D1 plus the
blank-line cleanup**. An earlier draft credited the single drop to `test_lesson_id_scanner.py` and named
`test_warnings_classify.py` as the floor at 406 while `test_lesson_id_scanner.py` was still flagged at
403; both statements were wrong when written. They are re-derived here at the moment of the claim.

This is a deliverable that was not attempted, not one attempted and failed. The reason is
scope-versus-budget: a safe split requires per-module analysis of which module-level constants, helpers
and fixtures each moved cluster depends on, and re-homing them without stranding a consumer. Across 53
modules that is the bulk of the plan's work. Splitting is also the one deliverable with **no**
line-count benefit — it adds a preamble per new module — so deferring it does not change the
§ Verification shortfall.

`test_claude_runtime.py`'s ~40 test classes remain the cluster boundaries a later run should use.

### D3 — preambles and argument construction — **partial**

**Preambles (B7): 46 → 17 findings.** 27 hand-rolled preambles across 15 modules now resolve by
`(bundle, skill, script)` identity: directory-counting constants became `get_scripts_dir(bundle,
skill)`, and `spec_from_file_location` / `module_from_spec` / `exec_module` triples became
`load_script_module`. **5 `spec_from_file_location` occurrences remain** in the slice, so the
done-when's first clause is **not** met.

**`parse_ns` (B6): not applied.** Re-derived at report time: the slice contains **210 `Namespace(`
constructions and 0 `parse_ns` call sites**. The plan asks for an exception list per call site that
`parse_ns` cannot serve; that list is **empty because the sweep did not run**, not because every call
site converted. Stating it the other way would be the false-clean signal this lane exists to prevent.

### D4 — parametrize tabular cases and strip history from prose — **partial**

**Prose (B3): 23 → 0 findings. This half is complete.** Each of the 23 was hand-rewritten:

* citations carrying a *mechanism* keep the mechanism and lose only the reference — "Regression guard
  for PR #380 … the previous implementation called `data.get('plan')` directly, which raises
  AttributeError" became "Calling `data.get('plan')` on a list or scalar raises AttributeError";
* fixture-provenance labels in `test_recipe_scoring.py` now state the fixture's **discriminating
  shape** (`# Surgical: root cause and exact change known, single file.`) rather than the archived PR;
* superseded-behaviour narration was rewritten to state what is true now.

The plan's warning was honoured: the docstrings explaining **why a seam is patched the way it is** —
the daemon-routing `__globals__` targeting and the `sys.modules` re-registration hazard — were read and
**left intact**; those four modules are byte-identical to base.

One docstring that D1 made untrue was repaired after review:
`test_file_ops.py::test_get_worktree_root_returns_plan_local_worktrees` described a "delenv + chdir"
arrangement that now happens at fixture setup rather than in the body. D4 owns prose truth, so this
counted as a D4 defect, not a D1 one.

**Parametrization (B5): one family of eleven collapsed; the rest not done.**
`extension-api/test_configurable_contract.py::TestMalformedDeclarations` — eleven tests differing only
in document body and expected message — is now one parametrized case with an `ids=` list carrying what
the eleven names said (−91 lines; collected count preserved, since each row is still one collected
item).

**Why the remainder was not swept mechanically:** measured structural similarity overstates
collapsibility. Strict AST-identity finds 39 families worth ~453 lines; relaxing to ≥80% skeleton
similarity finds 223 families worth ~4,554 lines — but that looser set is unsafe to apply
mechanically, because the plan's own Out-of-scope names `test/plan-marshall/script-shared/`'s **matched
positive/negative control pairs**, whose arms are evidence only in contrast and which have exactly the
shape a similarity scan reports as duplicates. Collapsing those leaves the suite green while voiding
the evidence. Each family needs reading; this run read one.

### D5 — property-based-testing candidate list — **done**

A **report deliverable**; no dependency was added and no property-based test was written.

**Derivation, not a copy.** Plan `010` § D6 fixed the method and column set for the whole tree (107
functions across 53 modules); this narrows it to the production modules **this slice's test directories
exercise**, using `010`'s own universal-contract name shapes (`parse*`, `validate*`, `normali[sz]e*`,
`encode`/`decode`, `serial`/`deserial`, `canonicalize`, `slugify`, `escape`/`unescape`, `coerce`,
`to_toon`/`from_toon`), filtered to those actually called by a slice test today.

**Result: 38 candidate units across 9 of the 15 slice directories — 9 refining `010`'s whole-tree list
and 29 new.** (An earlier draft said 39 and 30; the table below enumerates 38, and the corrected split
is 9 + 29.) "Example rows" counts the call sites the current tests use — the hand-picked examples a
generator would replace.

| Unit | Tested today by | Property that would be asserted | Example rows | vs `010` |
|---|---|---|---|---|
| `toon_parser.parse_toon` / `serialize_toon` | `ref-toon-format/test_toon_parser.py` | round-trip: `parse_toon(serialize_toon(x)) == x` for all valid documents | 26 / 6 | refines |
| `toon_parser.parse_toon_table` | `ref-toon-format/test_toon_parser.py` | every well-formed table parses to a row list of the declared arity | 5 | refines |
| `argparse_surface.parse_choice_list` | `script-shared/test_argparse_surface.py` | output is always a list of the literal choices, order-preserving | 3 | refines |
| `argparse_surface.parse_flag_arity` | `script-shared/test_argparse_surface.py` | arity is a non-negative int or the variadic sentinel, never other | 4 | refines |
| `argparse_surface.parse_help_node` | `script-shared/test_argparse_surface.py` | any `--help` output parses without raising | 1 | refines |
| `argparse_surface.parse_required_flags` | `script-shared/test_argparse_surface.py` | result ⊆ the flags the surface declares | 1 | refines |
| `permission_fix.normalize_path_perm` | `tools-permission-fix/test_permission_fix_behavior.py` | idempotent: `f(f(x)) == f(x)`; never emits a trailing slash | 4 | refines |
| `file_ops.parse_markdown_metadata` | `tools-file-ops/test_file_ops.py` | round-trips against `generate_markdown_metadata` | 5 | refines |
| `permission_fix.parse_timestamped_permission` | `tools-permission-fix/test_permission_fix_behavior.py` | round-trips against the timestamp writer | 3 | **new** |
| `input_validation.validate_plan_id` | `tools-input-validation/test_input_validation.py` | accepts exactly the documented id grammar; total on `str` | 16 | **new** |
| `input_validation.validate_relative_path` | `tools-input-validation/test_input_validation.py` | never accepts a path escaping the root (`..`, absolute, symlink-shaped) | 11 | **new** |
| `input_validation.validate_script_notation` | `tools-input-validation/test_input_validation.py` | accepts exactly `bundle:skill:script`; total on `str` | 9 | **new** |
| `input_validation.validate_skill_notation` | `tools-input-validation/test_input_validation.py` | accepts exactly `bundle:skill`; total on `str` | 7 | **new** |
| `input_validation.validate_session_id` | `tools-input-validation/test_input_validation.py` | total on `str`; rejects every non-member | 5 | **new** |
| `input_validation.validate_enum` | `tools-input-validation/test_input_validation.py` | total on `str`; rejects every non-member | 5 | **new** |
| `input_validation.validate_component` | `tools-input-validation/test_input_validation.py` | total on `str`; grammar-exact | 3 | **new** |
| `input_validation.validate_package_name` | `tools-input-validation/test_input_validation.py` | total on `str`; grammar-exact | 3 | **new** |
| `input_validation.validate_phase_id` | `tools-input-validation/test_input_validation.py` | total on `str`; grammar-exact | 3 | **new** |
| `input_validation.validate_hash_id` | `tools-input-validation/test_input_validation.py` | total on `str`; grammar-exact | 2 | **new** |
| `input_validation.validate_task_number` | `tools-input-validation/test_input_validation.py` | total on `str`; grammar-exact | 2 | **new** |
| `input_validation.validate_lesson_id` | `tools-input-validation/test_lesson_id_scanner.py` | total on `str`; grammar-exact | 1 | **new** |
| `input_validation.validate_task_id` | `tools-input-validation/test_input_validation.py` | total on `str`; grammar-exact | 1 | **new** |
| `input_validation.parse_args_with_toon_errors` | `tools-input-validation/test_router_flag_placement.py` | any argv yields a namespace or a structured error, never a crash | 3 | **new** |
| `schema_validation.validate_status` | `tools-input-validation/test_schema_validation.py` | any dict input yields a verdict, never raises | 18 | **new** |
| `schema_validation.validate_task` | `tools-input-validation/test_schema_validation.py` | as above | 13 | **new** |
| `schema_validation.validate_references` | `tools-input-validation/test_schema_validation.py` | as above | 7 | **new** |
| `schema_validation.validate_assessment` | `tools-input-validation/test_schema_validation.py` | as above | 6 | **new** |
| `schema_validation.validate_finding` | `tools-input-validation/test_schema_validation.py` | as above | 6 | **new** |
| `extension_base.validate_tree_completeness` | `script-shared/test_extension_base*.py` | verdict is total over any tree shape | 10 | **new** |
| `_build_result.validate_result` | `script-shared/test_build_result.py` | verdict is total over any result dict | 10 | **new** |
| `sensible_number.parse_sensible_int` | `script-shared/test_sensible_number.py` | total on `str`; never returns a non-int | 5 | **new** |
| `triage_helpers.parse_json_arg` | `script-shared/test_triage_helpers.py` | any `str` yields a value or a named error, never a crash | 3 | **new** |
| `pretooluse_gate.parse` | `platform-runtime/test_pretooluse_gate.py`, `test_permission_ops.py` | any hook payload parses to a decision, never raises | 13 | **new** |
| `platform_runtime._parse_json_list` | `platform-runtime/test_platform_runtime_router.py` | total on `str`; never returns a non-list | 5 | **new** |
| `platform_runtime._parse_context` | `platform-runtime/test_platform_runtime_router.py` | total on `str`; never returns a non-list | 3 | **new** |
| `configurable_contract.parse_configurable` | `extension-api/test_configurable_contract.py` | every malformed doc raises `ValueError`, never returns a partial | 7 | **new** |
| `_list_providers._validate_provider_selection` | `manage-providers/test_list_providers.py` | verdict is total over any selection string | 7 | **new** |
| `generate_executor.parse_template_format_version` | `tools-script-executor/test_generate_executor.py` | total on `str`; never returns a malformed version | 1 | **new** |

**Relationship to `010`'s whole-tree list.** The 9 refining rows are the ones `010` named that fall
inside this slice (the `toon_parser` triple, the four `argparse_surface` derivations,
`normalize_path_perm`, `parse_markdown_metadata`). The 29 new rows are dominated by the
`tools-input-validation` validator family, which is where this slice concentrates and which is by far
the densest cluster of genuinely universal contracts in the tree. The operator receives one list
refined, not a third unrelated table.

One of `010`'s three seeds resolves to nothing here, and `010` recorded the same: the
`doctor-test-conventions.md` § "Rule 3 — Validator Registry" is **empty**, contributing no call sites.
Independently confirmed.

**The plan's `HYPOTHESIS` claim for D5 is settled: the slice does contain units whose contract is
universal in the B8 sense, and there are many** — 38, concentrated in the validator and parser
families. The plan invited a plain "few or none"; the derivation did not support one, and the table is
not padded.

### D6 — measured deltas — **done**

All six figures, each with the command that produced it, re-derived at report time.

**1. Line counts, per directory and slice total:**

| Directory | before | after | Δ |
|---|---:|---:|---:|
| extension-api | 5,710 | 5,622 | −88 |
| lsp-client | 616 | 616 | 0 |
| manage-files | 1,746 | 1,700 | −46 |
| manage-logging | 1,651 | 1,635 | −16 |
| manage-providers | 4,171 | 4,163 | −8 |
| platform-runtime | 13,454 | 13,391 | −63 |
| ref-toon-format | 854 | 854 | 0 |
| script-shared | 15,232 | 15,113 | −119 |
| tools-file-ops | 2,410 | 2,378 | −32 |
| tools-input-validation | 1,587 | 1,505 | −82 |
| tools-permission-doctor | 846 | 846 | 0 |
| tools-permission-fix | 1,857 | 1,859 | **+2** |
| tools-script-executor | 11,316 | 11,297 | −19 |
| untrusted-ingestion | 201 | 201 | 0 |
| `test/pm-code-intelligence/` | 260 | 260 | 0 |
| **TOTAL (15-dir, 118 modules)** | **61,911** | **61,467** | **−444 (−0.72%)** |

`tools-permission-fix` grew by 2: two fixtures replaced fewer inline call sites than their own
definitions cost. That is a real regression against the line target, left visible rather than netted
away.

**2. Collected test count** — `uv run python -m pytest <15 dirs> --collect-only -q -o addopts=""`:

| before | after |
|---:|---:|
| **3,827** | **3,827** |

Unchanged — condition (1). **Unit matters:** this is pytest's **collected-item** count, so the
eleven-row parametrization contributes eleven items exactly as the eleven functions did. The count of
test **functions** fell (3,328 → 3,318); the collected count did not, and the collected count is what
the gate names.

**3. Coverage** — `pytest <15 dirs> --cov=marketplace/bundles/plan-marshall/skills
--cov=marketplace/bundles/pm-code-intelligence/skills --cov-report=term`, at HEAD and again in a
detached worktree at the branch base `5edca5a`:

| | statements | missed | branches | partial | coverage |
|---|---:|---:|---:|---:|---:|
| before (`5edca5a`) | 18,203 | 6,646 | 6,864 | 664 | **61%** |
| after (HEAD) | 18,203 | 6,646 | 6,864 | 664 | **61%** |

Byte-identical — the expected result for a change that moves no production code and deletes no
assertion. Condition (2) holds. (Assertion count 3,363 → 3,359; all four removed are
`assert _spec is not None` loader guards inside preambles D3 replaced, not test assertions.)

**4. `monkeypatch`-to-fixture ratio** — 15-dir **17.70 : 1 → 6.38 : 1**; 14-dir **17.62 : 1 → 6.35 : 1**.

**5. `parse_ns` exception list** — **empty because the B6 sweep did not run** (D3 above). 210
`Namespace(` constructions and 0 `parse_ns` call sites remain in the slice. Not to be read as "no
exceptions found".

**6. `plugin-doctor test-conventions` per-rule counts** — the invocation from
`doc/plans/test-quality/README.md` § "Running the plugin-doctor test-conventions scope", run per
directory over the 15 and summed. It ran unmodified; the five-directory `PYTHONPATH` sufficed, so no
sixth directory needs adding:

| Rule | before | after | Δ |
|---|---:|---:|---:|
| `test-module-line-budget` | 55 | 53 | −2 |
| `test-module-preamble-boilerplate` | 46 | 17 | **−29** |
| `test-docstring-historical-prose` | 23 | **0** | **−23** |
| `subprocess-pythonpath` | 3 | 3 | 0 |
| `unique-fixture-basenames` | 0 | 0 | 0 |
| `test-helper-module-misnamed` | 0 | 0 | 0 |
| `identifier-validator-corpus` | 0 | 0 | 0 |
| **TOTAL** | **127** | **73** | **−54 (−43%)** |

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty — 37 test modules** (39 files
changed in total, the other two being this report and the epic's findings document). The gate applies.

Per-commit `./pw quality-gate` ran clean before every commit touching `*.py`: `ruff … All checks
passed!`, `mypy … Success: no issues found in 408 source files`, `SPDX-header check passed`.

## Verification

**The three-part done-when. Two of three hold.**

| # | Condition | Result |
|---|---|---|
| 1 | Collected test count does not decrease | **PASS** — 3,827 → 3,827 |
| 2 | Coverage does not decrease | **PASS** — 61% → 61%, statement-for-statement identical |
| 3 | Line count drops ≥25% | **FAIL — 0.72% against a 25% floor** |

### The line-floor shortfall, and why it is reported rather than closed

The plan's instruction for this case is explicit: *"If it cannot be reached without violating (1) or
(2), report the shortfall and stop."* This run reached 0.72%. The floor needed **≥15,478 lines**
removed; **444** were.

The shortfall is structural, not a consequence of stopping early on one deliverable:

* **The slice is already lean per test.** Mean test function: **11.7 lines including its docstring** —
  *inside* B2's 15-line budget. Composition: 20.1% blank, 8.2% comment, 15.3% docstring, 56.4% code;
  63% of all lines sit inside test function bodies.
* **Every remaining lever, summed at its optimistic estimate, falls short:**

  | Lever | Optimistic estimate |
  |---|---:|
  | Parametrization at ≥80% skeleton similarity (223 families) | ~4,554 |
  | Banner/divider comment blocks | ~1,500 |
  | Remaining preamble normalisation | ~400 |
  | Remaining fixture hoisting | ~150 |
  | **Total available** | **~6,600 (10.7%)** |

  Optimistic twice over: the ≥80% set includes the matched control pairs the plan forbids collapsing,
  and the banner sweep is **not a declared deliverable** — stripping it would be undeclared collateral.

Closing the remaining ~24 points would require deleting assertions, violating condition (1) and
committing the failure the epic README names outright: *"Any plan in this epic that deletes an
assertion to hit a line target has failed, not succeeded."* The floor is reported unmet and the
assertions are intact — the plan's own Notes applied: *"Where a reduction and a hermeticity guarantee
conflict, the guarantee wins and the shortfall goes in the report."*

**The 25% figure appears to have been set from the corpus-wide profile rather than this slice's** —
recorded as F5, a finding about the plan rather than an excuse.

### The fourth check — hermeticity. **The suite is NOT order-independent.**

An earlier draft of this report claimed `pytest-xdist` was unavailable and concluded *"This check was
run and passes"* on three same-order runs. **Both halves of that were wrong**, and the correction
inverts the verdict.

**`pytest-xdist` IS installed.** The plan's `-n auto` arm was available all along and has now been run:

| Arm | Command | Result |
|---|---|---|
| Default order, serial | `pytest <15 dirs> -o addopts="" -q` | **3,827 passed** |
| **Parallel** | `pytest <15 dirs> -o addopts="" -q **-n auto**` | **3,827 passed** in 100.8s |
| **Reverse directory order** | same 15 paths, reversed | **1 failed, 3,826 passed** |

`pytest-randomly` is genuinely absent — but reordering never required it, and passing the directories
in reverse order is a sufficient reordering. Doing so surfaces a real failure:

```
FAILED test/plan-marshall/platform-runtime/test_layout_resolution.py::test_resolve_module_reimport_clean
E   ImportError: module marketplace_paths not in sys.modules
```

**Root cause** — `test/plan-marshall/extension-api/test_extension_discovery.py:71` calls
`load_script_module('plan-marshall', 'script-shared', 'marketplace_paths.py')` with **no
`module_name`**, so it registers under the stem and **overwrites `sys.modules['marketplace_paths']` at
collection time**. When `extension-api` is collected after `platform-runtime`, the object
`test_layout_resolution.py` holds is no longer the registered one and `importlib.reload` raises.

**This is pre-existing, not introduced by this branch** — independently confirmed by running the
identical reverse order in a detached worktree at `5edca5a`, where it fails identically (`1 failed,
3826 passed`). It is nonetheless **inside this plan's own Expected surface**, and it is exactly what
the plan's fourth check was written to catch. It is **not fixed here** (it is outside D1–D6 and the fix
touches module-registration semantics) and is carried at § Residue as the highest-priority item.

So the honest verdict: **the parallel arm passes; the reordering arm fails on a pre-existing defect;
the suite is repeatable but not order-independent.**

### The cold read — D4's required by-reading check

**Not performed.** The plan requires dispatching a sub-agent with five rewritten modules **and no other
context**, asking for ten named tests what contract each pins and why. D4's prose half landed, so the
check has a subject; it was not run, and no answers are recorded. Reported as not done rather than
approximated by the general verification pass (F6).

### Executable

`./pw verify` — **`=== verify: SUCCESS ===`**, whole-tree: **20,272 passed, 14 skipped, 0 failed** in
623s. All three sub-steps ran, which matters because two are the ones a narrower call would skip:
`quality-gate` (ruff / mypy(production) over 408 files / SPDX / plugin-doctor), **`test-compile` (mypy
over the whole test tree, 760 files)**, and `module-tests`. The lane warns that substituting
`quality-gate` + a scoped `module-tests` lets a test-only type error through to CI; the full gate ran.

## Findings

Recorded per instance.

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | D1 automated pass | `test__claude_runtime_impl.py::TestSessionRenderTitleNamedOutcomes` repeats `monkeypatch.setattr("sys.stdout", _RaisingStdout())` in 4 tests, so it scans as a B4 candidate | **Rejected, with reason.** Those tests call `monkeypatch.undo()` part-way through the body; *where* the patch is applied is the contract. Hoisting it broke 4 tests, which is how it was caught. Left inline as a genuine per-test need |
| F2 | D3 conversion | `tools-script-executor/test_execute_script.py:31` resolved `LOGGING_DIR` through `skills/logging/scripts`, **which does not exist**. The raw `Path` chain silently produced a non-existent directory, substituted into the generated executor under test | **Fixed** — now `get_scripts_dir('plan-marshall', 'manage-logging')`. Surfaced only because `get_scripts_dir` raises where a raw `Path` does not |
| F2b | Verification sweep | **The same defect survived in two sibling modules** an earlier draft's "Fixed" disposition did not cover: `test_executor_runtime.py:59` (whose docstring claims it points at "the **real** marketplace location") and `test_executor_integration.py:30`. `test_executor_runtime.py` was itself modified by this branch | **Fixed** — both now resolve `manage-logging`. A sweep of every `MARKETPLACE_ROOT`-anchored skill path across all 15 directories finds no further nonexistent-skill construction |
| F3 | D1 tooling | First hoist attempt spliced a fixture into a **triple-quoted string literal**, because the module-scope insertion point was found by matching `^import ` over raw lines and `test_generate_executor.py` embeds `import sys` inside a script fixture | **Fixed in tooling** (AST-derived insertion point); corrupted state reverted before any commit |
| F4 | D1 tooling | Second attempt stacked `@pytest.fixture()` decorators, because `FunctionDef.lineno` points at `def`, not at the decorator | **Fixed in tooling**; reverted before commit |
| F5 | This run, against the plan | The 25% line floor is unreachable for this slice without deleting assertions. Mean test is already 11.7 lines, inside B2's budget | **Reported, not closed.** Proposal to the epic: set line floors per-slice from that slice's own composition |
| F6 | Lane self-check | D4's required cold-read verification was not performed | **Reported as not done** |
| F7 | Partition gate | `test/pm-code-intelligence/` is claimed by no plan in `030`–`080` | **Escalated; claimed by operator decision.** The directory still carries an unfixed D3 finding — § Residue |
| F8 | D3 | 17 preamble findings, 5 `spec_from_file_location`, and the whole B6 `parse_ns` sweep remain | **Deferred** — § Residue |
| F9 | Verification sweep | **The reordering arm was skipped on a false premise** (`pytest-xdist` reported absent when installed), and the hermeticity verdict was stated as passing on same-order runs alone | **Fixed** — `-n auto` run (passes) and reverse-order run (fails); § Verification rewritten and the verdict inverted |
| F10 | Verification sweep | Reverse-order collection fails: `test_extension_discovery.py:71` overwrites `sys.modules['marketplace_paths']` | **Recorded, not fixed** — pre-existing at base (independently confirmed), outside D1–D6, and the fix touches registration semantics. § Residue, highest priority |
| F11 | Verification sweep | **D3 newly registers six colliding names in `sys.modules`.** The base `_load_module` helpers used bare `spec_from_file_location` with no `sys.modules` write; `conftest.load_script_module` **does** register. `_build_parse`, `_build_shared`, `_build_result`, `_build_format`, `_build_discover`, `_extension_constants` are now published by slice tests, and `_build_parse`/`_build_shared` are plain-imported by eight modules in six directories owned by **concurrently-running sibling plans** | **Latent, recorded as a proposal.** Whole tree green in both orders, so nothing is live. But it is F10's mechanism multiplied by six. **Proposal:** `load_script_module` should take an opt-out of `sys.modules` registration, or callers loading a name that is also plain-imported elsewhere should pass a distinct `module_name`. Per the plan, a needed `conftest.py` change is a proposal, not an edit |
| F12 | Verification sweep | Six numeric errors in the first draft: the D2 drop credited to the wrong module and the wrong floor named; "117 modules" for a 15-directory population; the ratio quoted over 14 directories inside 15-directory framing; "278 call sites" when 278 was a rewrite count; D5 totalled 39/30 against a 38-row table | **All corrected above**, each re-derived at the moment of the claim |
| F13 | Verification sweep | Machine-generation residue: 9 module constants left dead by D3; a duplicate `in_tmp_cwd` shadowing an identical module-level fixture; 13 blank lines left directly under signatures; 3 malformed single-line calls | **Fixed** |
| F14 | Verification sweep | `test_get_worktree_root_returns_plan_local_worktrees`'s docstring described an arrangement D1 had changed | **Fixed** — D4 owns prose truth |
| F15 | Plan-directory step | Moving the plan to `…/plan.md` broke three inbound links in `findings-test-corpus-review.md` (lines 73, 302, 304) — undeclared collateral of Step 3 | **Fixed** — the file already carried `010-…/plan.md` and `020-…/plan.md`, so the convention existed and was simply not followed |
| F16 | D1 review | Two residual groups were mischaracterised as "genuine per-test needs" when the only test-local name was a function-local import | **Fixed** — 11 further sites hoisted; the third such group is § Residue |

## Reviewer participation

_(completed at the merge gate — see below)_

## Cost

* **Tokens:** not available to the agent in this session — the harness exposes no token counter to the
  running agent, so no figure is stated rather than an invented one. The verification sub-agent's own
  usage was reported to the parent as ~242k tokens over 173 tool calls.
* **Wall-clock:** ~5h session start to merge gate, dominated by test and coverage runs (full-slice
  serial pytest ~3.5 min; `-n auto` ~1.7 min; each coverage pass ~4–5.5 min; whole-tree `./pw verify`
  ~10.4 min).
* **Population:** one Claude Code cloud session executing one `doc/plans/` plan end to end, plus one
  dispatched verification sub-agent. ⛔ **NOT comparable to a plan-marshall `metrics.toon` total**,
  which counts an orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing
  boundary. This run has no such boundary; the figures cannot be reconciled and no parity is implied.

## Contract check (Step 9)

_(completed as the final pre-merge commit — see below)_

## What have we learned (Step 9)

_(completed as the final pre-merge commit — see below)_

## Residue

Open, in priority order:

1. **F10 — the order-dependent failure.** `test_extension_discovery.py:71` must pass a distinct
   `module_name` (or the test must not clobber the shared registration). Pre-existing, but inside this
   slice and the reason the plan's fourth check exists. **The suite is not order-independent until this
   is fixed.**
2. **F11 — the six new `sys.modules` registrations**, three of which sibling plans' directories
   plain-import. Latent today; the proposal is in F11.
3. **D2 in full — 53 modules over budget.** Largest: `test_claude_runtime.py` (4,668, ~40 classes —
   its classes are the cluster boundaries), `test_generate_executor.py` (3,106),
   `test__claude_runtime_impl.py` (1,999), `test_execute_script.py` (1,808).
4. **D4 parametrization beyond the one landed family** — 223 families at ≥80% similarity, ~4,554 lines.
   Each needs reading, and `script-shared`'s matched control pairs must be excluded by hand.
5. **D3's B6 `parse_ns` sweep** — not started; 210 `Namespace(` constructions, 0 `parse_ns`. Plus 17
   preamble findings and 5 `spec_from_file_location`.
6. **`test/pm-code-intelligence/`'s own D3 finding** (F7) — claimed into scope but not brought up to
   standard.
7. **The third D1 group** (F16) — `TestSessionRenderTitleSessionTitleEmit`'s ×3 `sys.stdin` redirect is
   a missing fixture, not a per-test need.
8. **The hermeticity check's randomised arm** — `pytest-randomly` is absent here.
9. **D4's cold read** (F6).
10. **The partition defect (F7)** — `test/pm-code-intelligence/` needs assigning to a plan by the epic
    owner. This run's claim was a decision about *this run*, not a durable partition fix.
11. **Proposal to the epic (F5)** — set per-slice line floors from each slice's own composition.
