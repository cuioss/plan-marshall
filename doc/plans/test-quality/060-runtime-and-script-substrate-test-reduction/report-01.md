# Run report — 060-runtime-and-script-substrate-test-reduction (run 01)

**Date (UTC):** 2026-08-16    **Branch:** `claude/runtime-script-substrate-tests-qqeuoj`    **PR:** _(pending)_    **Outcome:** partial

The slice's house-style deliverables (D1, D3, D4, D5) landed and are measured below. **D2 did not
land**, and the plan's 25% line floor was not reached — by a wide margin. Both are stated in full at
§ Verification and § Residue rather than softened here.

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
| Plans `010` and `020` landed | **PASS** — `parse_ns` at `test/conftest.py:569`; the 400-line module budget is in `persona-module-tester/standards/testing-methodology.md:75` |
| No property-based test exists tree-wide | **CONFIRMED** — `grep -rn 'hypothesis\|@given\|strategies' test --include=*.py` returns 3 hits, all incidental (a `test_strategies_are_distinct_objects` about re-review strategy objects, a docstring reading "capture strategies", the word "hypothesised"). No Hypothesis import, no `@given`. D5's table therefore starts from zero, as the plan's fallback says |
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
unilaterally. The operator was reachable, so the decision was escalated via `AskUserQuestion` rather
than taken here.

**Question asked:** whether to (a) record the defect and execute plan 060's own cleanly-claimed slice,
(b) halt entirely, or (c) claim the directory into this plan and refactor it. Option (c) was presented
as **not recommended**, with the reason stated: the plan and the epic README both forbid claiming an
unclaimed entry unilaterally, and a concurrent sibling may later claim it.

**Operator answer:** *"Add it to 060's slice and refactor it"* — option (c).

That decision is recorded here as an **operator-authorised deviation** from the plan's stated
constraint, so the epic owner sees both the partition defect and its disposition. The working surface
for this run is therefore **15 directories**: the plan's fourteen plus `test/pm-code-intelligence/`.
In the event the directory needed no change under any deliverable, so the deviation altered no file —
but the claim itself still stands as a deviation, and a future plan assigning that directory is not
in conflict with anything this run wrote.

## Deliverables

| # | Deliverable | State | Commit |
|---|---|---|---|
| D1 | Hoist repeated isolation setup into fixtures | **done** | `8d924e3` |
| D2 | Split every module over the budget | **NOT DONE** | — |
| D3 | Normalise preambles and argument construction | **partial** | `a8bc055` |
| D4 | Parametrize tabular cases; strip history from prose | **partial** (prose half complete) | `48d8c30`, `21e46cb` |
| D5 | Derive the property-based-testing candidate list | **done** (report deliverable) | this report |
| D6 | Report the measured deltas | **done** | this report |

### D1 — isolation setup hoisted into fixtures — **done**

278 inline `monkeypatch` call sites across 18 modules collapsed into 46 fixtures, each **explicitly
requested by name**; none is `autouse`, as the plan and `persona-module-tester` § "Compose Isolation,
Don't Impose It" require.

Candidates were selected mechanically: an isolation call repeated in ≥3 tests of one class or module,
**and** whose free names all bind at module level (so the fixture body cannot capture a per-test
local). 46 of the 83 raw repetition groups met that bar; the other 37 depend on values computed inside
the test and are genuine per-test needs, not missing fixtures.

**The plan's worked case is included:** `test_claude_runtime.py::TestReadActiveOrchestrator` and three
classes of `test__claude_runtime_impl.py` no longer repeat the `_SESSION_CACHE_BASE` redirect per test —
they request a `session_cache_base` fixture.

**Ratio before/after, as the deliverable requires:**

| | `monkeypatch.setattr`+`setenv` | `@pytest.fixture` | ratio |
|---|---|---|---|
| before | 652 | 37 | **17.62 : 1** |
| after | 542 | 83 | **6.53 : 1** |

Command: counted over the slice's `test_*.py` with `str.count` per file (script retained in the run's
scratch, not committed — it is a measurement, not a deliverable).

**One candidate group was deliberately rejected** — see Findings F1.

**By reading, as the plan's Verification requires.** Every fixture D1 introduced was re-read from its
own definition. All 46 are `@pytest.fixture()` with no `autouse=True`, and all are function-scoped —
which is the narrowest scope that can serve them, because each composes `tmp_path` and/or `monkeypatch`,
both of which pytest defines as function-scoped. A broader scope is therefore not merely unnecessary
here but unavailable. **No scope errors are left in place**, so the plan's "report any you leave in
place and why" has an empty answer, and this sentence is what makes that emptiness legible.

### D2 — split every module over the budget — **NOT DONE**

**No module was split. 54 of 117 modules in the slice remain over the 400-line budget**, from
`platform-runtime/test_claude_runtime.py` at 4,667 lines down to `test_warnings_classify.py` at 406.
The count moved 55 → 54 only because `test_lesson_id_scanner.py` fell under budget as a side effect of
D1 and D4.

This is a deliverable that was not attempted, not one that was attempted and failed, and it is not
reported as anything else. The reason is scope-versus-budget: a safe split requires per-module analysis
of which module-level constants, helpers and fixtures each moved cluster depends on, and re-homing them
without stranding a consumer. Across 54 modules that is the bulk of the plan's work, and this run spent
its budget on D1/D3/D4/D5 instead. Splitting is also the one deliverable with **no** line-count benefit
— it adds a preamble per new module — so deferring it does not change the § Verification shortfall
below.

`test_claude_runtime.py`'s ~40 test classes remain the cluster boundaries a later run should use, as
the plan says; the module now has 40 classes and 4,667 lines.

### D3 — preambles and argument construction — **partial**

**Preambles (B7): 46 → 17 findings.** 27 hand-rolled preambles across 15 modules now resolve by
`(bundle, skill, script)` identity:

* directory-counting constants (`Path(__file__).parent.parent.parent.parent / 'marketplace' / ...`)
  became `get_scripts_dir(bundle, skill)`;
* `spec_from_file_location` / `module_from_spec` / `exec_module` triples became `load_script_module`.

The 17 remaining are a mix the automated pass deliberately did not touch: path constants that do not
terminate at a `scripts/` directory, and loaders whose target path is computed per-call. They are real
findings and are left for a follow-up.

**`parse_ns` (B6): not applied — and the plan's "record the call site" clause is why this is reported
rather than silently skipped.** The B6 conversion of hand-built `argparse.Namespace` objects was not
started in this run. This is under-delivery against D3, not a set of individual exceptions, so the
plan's per-call-site exception list is **empty for the reason that the sweep did not run** — not
because every call site converted cleanly. Stating it the other way would be the false-clean signal
this lane exists to prevent.

### D4 — parametrize tabular cases and strip history from prose — **partial**

**Prose (B3): 23 → 0 findings. This half is complete**, which is the deliverable's stated done-when for
prose. Each of the 23 was hand-rewritten, never pattern-substituted:

* citations that carried a *mechanism* keep the mechanism and lose only the reference — e.g. "Regression
  guard for PR #380 … the previous implementation called `data.get('plan')` directly, which raises
  AttributeError" became "Calling `data.get('plan')` on a list or scalar raises AttributeError";
* fixture-provenance labels in `test_recipe_scoring.py` (`# PR #866 — fix-check-era-stamps …`) now state
  the fixture's **discriminating shape** (`# Surgical: root cause and exact change known, single file.`),
  which is what makes the row a MATCH case — strictly more useful to a reader than the PR number;
* superseded-behaviour narration ("that validator was removed in plan …") was rewritten to state what
  is true now.

The plan's warning was honoured: the docstrings explaining **why a seam is patched the way it is** —
the daemon-routing `__globals__` targeting and the `sys.modules` re-registration hazard — were read and
**left intact**. They carry no citation, so the rule never flagged them, and none was touched.

**Parametrization (B5): one family of eleven collapsed; the rest not done.**
`extension-api/test_configurable_contract.py::TestMalformedDeclarations` — eleven tests differing only
in document body and expected message — is now one parametrized case with an `ids=` list carrying what
the eleven names said (−91 lines, collected count unchanged). The remaining families were not
converted.

**Why the remaining families were not simply swept:** measured structural similarity overstates
collapsibility here. Strict AST-identity finds 39 families worth ~453 lines; relaxing to ≥80% skeleton
similarity finds 223 families worth ~4,554 lines, but that looser set is not safe to apply
mechanically — the plan's own Out-of-scope names `test/plan-marshall/script-shared/`'s **matched
positive/negative control pairs**, whose arms are evidence only in contrast and which have exactly the
shape a similarity scan reports as duplicates. Collapsing those would leave the suite green while
voiding the evidence. Each family needs reading, and this run read one.

### D5 — property-based-testing candidate list — **done**

A **report deliverable**; no dependency was added and no property-based test was written, per Out of
scope.

**Derivation, not a copy.** Plan `010` § D6 fixed the method and the column set for the whole tree
(107 functions across 53 modules); this narrows it to the production modules **this slice's test
directories exercise**, using `010`'s own universal-contract name shapes (`parse*`, `validate*`,
`normali[sz]e*`, `encode`/`decode`, `serial`/`deserial`, `canonicalize`, `slugify`, `escape`/`unescape`,
`coerce`, `to_toon`/`from_toon`), filtered to those actually called by a test in the slice today.

**Result: 39 candidate call sites across 9 of the 15 slice directories.** "Example rows" counts the
call sites the current tests use — the hand-picked examples a generator would replace.

| Unit | Tested today by | Property that would be asserted | Example rows | vs `010` |
|---|---|---|---|---|
| `toon_parser.parse_toon` / `serialize_toon` | `ref-toon-format/test_toon_parser.py` | round-trip: `parse_toon(serialize_toon(x)) == x` for all valid documents | 26 / 6 | refines `010` (named as its strongest candidate) |
| `toon_parser.parse_toon_table` | `ref-toon-format/test_toon_parser.py` | every well-formed table parses to a row list of the declared arity | 5 | refines `010` |
| `argparse_surface.parse_choice_list` | `script-shared/test_argparse_surface.py` | output is always a list of the literal choices, order-preserving | 3 | refines `010` |
| `argparse_surface.parse_flag_arity` | `script-shared/test_argparse_surface.py` | arity is a non-negative int or the variadic sentinel, never other | 4 | refines `010` |
| `argparse_surface.parse_help_node` | `script-shared/test_argparse_surface.py` | any `--help` output parses without raising | 1 | refines `010` |
| `argparse_surface.parse_required_flags` | `script-shared/test_argparse_surface.py` | result ⊆ the flags the surface declares | 1 | refines `010` |
| `permission_fix.normalize_path_perm` | `tools-permission-fix/test_permission_fix_behavior.py` | idempotent: `f(f(x)) == f(x)`; never emits a trailing slash | 4 | refines `010` |
| `permission_fix.parse_timestamped_permission` | `tools-permission-fix/test_permission_fix_behavior.py` | round-trips against the timestamp writer | 3 | **new** |
| `input_validation.validate_plan_id` | `tools-input-validation/test_input_validation.py` | accepts exactly the documented id grammar; total on `str` | 16 | **new** |
| `input_validation.validate_relative_path` | `tools-input-validation/test_input_validation.py` | never accepts a path escaping the root (`..`, absolute, symlink-shaped) | 11 | **new** |
| `input_validation.validate_script_notation` | `tools-input-validation/test_input_validation.py` | accepts exactly `bundle:skill:script`; total on `str` | 9 | **new** |
| `input_validation.validate_skill_notation` | `tools-input-validation/test_input_validation.py` | accepts exactly `bundle:skill`; total on `str` | 7 | **new** |
| `input_validation.validate_session_id` / `validate_enum` | `tools-input-validation/test_input_validation.py` | total on `str`; rejects every non-member | 5 / 5 | **new** |
| `input_validation.validate_component` / `validate_package_name` / `validate_phase_id` | `tools-input-validation/test_input_validation.py` | total on `str`; grammar-exact | 3 / 3 / 3 | **new** |
| `input_validation.validate_hash_id` / `validate_task_number` | `tools-input-validation/test_input_validation.py` | total on `str`; grammar-exact | 2 / 2 | **new** |
| `input_validation.validate_lesson_id` / `validate_task_id` | `test_lesson_id_scanner.py` / `test_input_validation.py` | total on `str`; grammar-exact | 1 / 1 | **new** |
| `schema_validation.validate_status` | `tools-input-validation/test_schema_validation.py` | any dict input yields a verdict, never raises | 18 | **new** |
| `schema_validation.validate_task` | `tools-input-validation/test_schema_validation.py` | as above | 13 | **new** |
| `schema_validation.validate_references` / `validate_assessment` / `validate_finding` | `tools-input-validation/test_schema_validation.py` | as above | 7 / 6 / 6 | **new** |
| `file_ops.parse_markdown_metadata` | `tools-file-ops/test_file_ops.py` | round-trips against `generate_markdown_metadata` | 5 | refines `010` |
| `extension_base.validate_tree_completeness` | `script-shared/test_extension_base*.py` | verdict is total over any tree shape | 10 | **new** |
| `_build_result.validate_result` | `script-shared/test_build_result.py` | verdict is total over any result dict | 10 | **new** |
| `sensible_number.parse_sensible_int` | `script-shared/test_sensible_number.py` | total on `str`; never returns a non-int | 5 | **new** |
| `triage_helpers.parse_json_arg` | `script-shared/test_triage_helpers.py` | any `str` yields a value or a named error, never a crash | 3 | **new** |
| `pretooluse_gate.parse` | `platform-runtime/test_pretooluse_gate.py`, `test_permission_ops.py` | any hook payload parses to a decision, never raises | 13 | **new** |
| `platform_runtime._parse_json_list` / `_parse_context` | `platform-runtime/test_platform_runtime_router.py` | total on `str`; never returns a non-list | 5 / 3 | **new** |
| `configurable_contract.parse_configurable` | `extension-api/test_configurable_contract.py` | every malformed doc raises `ValueError`, never returns a partial | 7 | **new** |
| `_list_providers._validate_provider_selection` | `manage-providers/test_list_providers.py` | verdict is total over any selection string | 7 | **new** |
| `generate_executor.parse_template_format_version` | `tools-script-executor/test_generate_executor.py` | total on `str`; never returns a malformed version | 1 | **new** |

**Relationship to `010`'s whole-tree list, stated as the plan requires.** 9 rows **refine** `010`'s
(the `toon_parser` triple, the four `argparse_surface` derivations, `normalize_path_perm`,
`parse_markdown_metadata`) — these are the rows `010` named that fall inside this slice. The remaining
30 are **new**: `010`'s name-shape sweep covered `marketplace/bundles/**` broadly, but the
`tools-input-validation` validator family is where this slice concentrates, and it is by far the
densest cluster of genuinely universal contracts in the tree. The operator receives one list refined,
not a third unrelated table.

One of `010`'s three seed examples resolves to nothing here, and `010` recorded the same: the
`doctor-test-conventions.md` § "Rule 3 — Validator Registry" is **empty**, so it contributes no call
sites. That is a confirmation of `010`'s Finding 4, independently reached.

**The `HYPOTHESIS` claim the plan set for D5 is settled: the slice does contain units whose contract is
universal in the B8 sense, and there are many of them** — 39, concentrated in the validator and parser
families. The plan invited a plain "few or none" answer if the derivation found little; it did not, and
the table is not padded to make that so.

### D6 — measured deltas — **done**

All six figures, each with the command that produced it. Every figure is re-derived at report time.

**1. Line counts, per directory and slice total** — `wc -l`-equivalent over `test_*.py`:

| Directory | before | after | Δ |
|---|---:|---:|---:|
| extension-api | 5,710 | 5,622 | −88 |
| lsp-client | 616 | 616 | 0 |
| manage-files | 1,746 | 1,708 | −38 |
| manage-logging | 1,651 | 1,638 | −13 |
| manage-providers | 4,171 | 4,163 | −8 |
| platform-runtime | 13,454 | 13,403 | −51 |
| ref-toon-format | 854 | 854 | 0 |
| script-shared | 15,232 | 15,126 | −106 |
| tools-file-ops | 2,410 | 2,378 | −32 |
| tools-input-validation | 1,587 | 1,521 | −66 |
| tools-permission-doctor | 846 | 846 | 0 |
| tools-permission-fix | 1,857 | 1,859 | **+2** |
| tools-script-executor | 11,316 | 11,297 | −19 |
| untrusted-ingestion | 201 | 201 | 0 |
| `test/pm-code-intelligence/` (claimed by deviation) | 260 | 260 | 0 |
| **TOTAL** | **61,911** | **61,492** | **−419 (−0.68%)** |

`tools-permission-fix` grew by 2: two fixtures replaced fewer inline call sites than their own
definitions cost. That is a real regression against the line target and is left visible rather than
netted away.

**2. Collected test count** — `uv run python -m pytest <15 dirs> --collect-only -q -o addopts=""`:

| before | after |
|---:|---:|
| **3,827** | **3,827** |

Unchanged, which is condition (1). Note the unit: this is pytest's **collected-item** count, so the
eleven-row parametrization contributes eleven items exactly as the eleven functions did. The count of
test **functions** fell (3,328 → 3,318); the collected count did not, and the collected count is what
the gate names.

**3. Coverage** — `pytest <15 dirs> --cov=marketplace/bundles/plan-marshall/skills
--cov=marketplace/bundles/pm-code-intelligence/skills --cov-report=term`, run at HEAD and again in a
detached worktree at the branch's base commit `5edca5a`:

| | statements | missed | branches | partial | coverage |
|---|---:|---:|---:|---:|---:|
| before (`5edca5a`) | 18,203 | 6,646 | 6,864 | 664 | **61%** |
| after (HEAD) | 18,203 | 6,646 | 6,864 | 664 | **61%** |

Byte-identical, which is the expected result for a change that moves no production code and deletes no
assertion. Condition (2) holds.

**4. `monkeypatch`-to-fixture ratio** — 17.62 : 1 → **6.53 : 1** (D1 above).

**5. `parse_ns` exception list** — **empty, because the B6 sweep did not run** (D3 above). Not to be
read as "no exceptions found".

**6. `plugin-doctor test-conventions` per-rule counts** — the invocation from
`doc/plans/test-quality/README.md` § "Running the plugin-doctor test-conventions scope", run per
directory over the 15 and summed. It ran without modification; the five-directory `PYTHONPATH` was
sufficient, so no sixth directory needs adding:

| Rule | before | after | Δ |
|---|---:|---:|---:|
| `test-module-line-budget` | 55 | 54 | −1 |
| `test-module-preamble-boilerplate` | 46 | 17 | **−29** |
| `test-docstring-historical-prose` | 23 | **0** | **−23** |
| `subprocess-pythonpath` | 3 | 3 | 0 |
| `unique-fixture-basenames` | 0 | 0 | 0 |
| `test-helper-module-misnamed` | 0 | 0 | 0 |
| `identifier-validator-corpus` | 0 | 0 | 0 |
| **TOTAL** | **127** | **74** | **−53 (−42%)** |

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** (18 test modules), so the gate
applies. `./pw verify` — see § Verification. The per-commit `./pw quality-gate` ran clean before every
commit that touched `*.py`: `ruff … All checks passed!`, `mypy … Success: no issues found in 408
source files`, `SPDX-header check passed`.

## Verification

**The three-part done-when. Two of three hold.**

| # | Condition | Result |
|---|---|---|
| 1 | Collected test count does not decrease | **PASS** — 3,827 → 3,827 |
| 2 | Coverage does not decrease | **PASS** — 61% → 61%, statement-for-statement identical |
| 3 | Line count drops ≥25% | **FAIL — 0.68% against a 25% floor** |

### The line-floor shortfall, and why it is reported rather than closed

The plan's instruction for this case is explicit: *"If it cannot be reached without violating (1) or
(2), report the shortfall and stop."* This run reached 0.68%. The floor needed **≥15,478 lines**
removed; **419** were.

The shortfall is not a consequence of stopping early on any one deliverable — it is structural, and the
measurements say so:

* **The slice is already lean per test.** Mean test function: **11.7 lines including its docstring**,
  which is *inside* B2's 15-line budget. Composition: 20.1% blank, 8.2% comment, 15.3% docstring, 56.4%
  code. 63% of all lines sit inside test function bodies.
* **Every remaining lever, summed at its optimistic estimate, does not reach the floor:**

  | Lever | Optimistic estimate |
  |---|---:|
  | Parametrization at ≥80% skeleton similarity (223 families) | ~4,554 |
  | Banner/divider comment blocks | ~1,500 |
  | Remaining preamble normalisation | ~400 |
  | Remaining fixture hoisting | ~150 |
  | **Total available** | **~6,600 (10.7%)** |

  And that total is optimistic twice over: the ≥80% similarity set includes the matched
  positive/negative control pairs the plan forbids collapsing, and the banner sweep is **not a declared
  deliverable of this plan** — stripping it would be undeclared collateral change.

Closing the remaining ~24 points would require deleting assertions, which violates condition (1) and is
the failure the epic README names outright: *"Any plan in this epic that deletes an assertion to hit a
line target has failed, not succeeded."* The floor is therefore reported as unmet, and the assertions
are intact. This is the plan's own Notes applied: *"Where a reduction and a hermeticity guarantee
conflict, the guarantee wins and the shortfall goes in the report."*

**The 25% figure appears to have been set from the corpus-wide profile rather than this slice's.** That
is a finding about the plan, recorded at § Findings F5, not an excuse offered here.

### The fourth check — hermeticity

The plan requires the slice to be run twice and produce identical results, because a fixture hoisted to
too broad a scope surfaces as an order-dependent failure rather than a compile error. **This check was
run and passes**, with a stated limitation:

* Run A — default order, in-process: **3,827 passed**.
* Run B — default order, re-run after the full D1/D3/D4 set: **3,827 passed**, identical.
* Run C — coverage run over the same 15 directories: **3,827 passed**.

**Limitation, stated rather than glossed:** `pytest-randomly` and `pytest-xdist` are **not** installed
in this environment, so the plan's `-p no:randomly`-equivalent reordering and its `-n auto` parallel arm
could **not** be run. The three runs above are same-order runs, so they demonstrate repeatability but
**not** order-independence. The plan says to report an unavailable measurement as unavailable rather
than substituting a weaker check: **the order-randomised and parallel arms are unavailable in this
session.** The structural argument that partially substitutes — every D1 fixture is function-scoped and
explicitly requested, so none can leak across tests — is stated at D1, but it is an argument, not the
measurement the plan asked for.

### The cold read — D4's required by-reading check

**Not performed.** The plan requires dispatching the sub-agent with five rewritten test modules **and no
other context**, asking for ten named tests what contract each pins and why it matters. D4's prose half
did land, so the check has a subject; it was not run, and its answers are therefore not recorded. This
is reported as not done rather than approximated by the general verification pass (§ Findings F6).

### Executable

`./pw verify` — result recorded at § Findings after the pre-PR run.

## Findings

Recorded per instance.

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | D1 automated pass | `test__claude_runtime_impl.py::TestSessionRenderTitleNamedOutcomes` repeats `monkeypatch.setattr("sys.stdout", _RaisingStdout())` in 4 tests, so it scans as a B4 candidate | **Rejected, with reason.** Those tests call `monkeypatch.undo()` part-way through the body; *where* the patch is applied is the contract. Hoisting it to setup broke 4 tests, which is how it was caught. Left inline as a genuine per-test need |
| F2 | D3 conversion | `tools-script-executor/test_execute_script.py` resolved `LOGGING_DIR` through `skills/logging/scripts`, **which does not exist**. The raw `Path` chain silently produced a non-existent directory that was then substituted into the generated executor under test. The module's own docstring says the placeholder is "wired to the REAL manage-logging" | **Fixed** — now `get_scripts_dir('plan-marshall', 'manage-logging')`. Surfaced only because `get_scripts_dir` raises where a raw `Path` does not; a latent defect the identity helper caught by construction |
| F3 | D1 tooling | First hoist attempt spliced a fixture into a **triple-quoted string literal**, because the module-scope insertion point was found by matching `^import ` over raw lines and `test_generate_executor.py` embeds `import sys` inside a script fixture | **Fixed in tooling** (AST-derived insertion point) and the corrupted state reverted before any commit. No bad state reached the branch |
| F4 | D1 tooling | Second attempt stacked `@pytest.fixture()` decorators, because `FunctionDef.lineno` points at `def`, not at the decorator, so each new block spliced between an existing decorator and its function | **Fixed in tooling**; reverted before commit |
| F5 | This run, against the plan | The plan's 25% line floor is not reachable for this slice without deleting assertions (§ Verification). The slice's mean test is already 11.7 lines, inside B2's budget | **Reported, not closed.** A proposal for the epic: floors should be set per-slice from that slice's own composition, since a slice already at the house style has no surplus to remove |
| F6 | Lane self-check | D4's required cold-read verification was not performed | **Reported as not done** (§ Verification) |
| F7 | Partition gate | `test/pm-code-intelligence/` is claimed by no plan in `030`–`080` | **Escalated to operator; claimed into this plan by operator decision** (§ Gating checks). Recorded for the epic owner |
| F8 | D3 | 17 preamble findings and the whole B6 `parse_ns` sweep remain | **Deferred** — named in § Residue |

## Reviewer participation

_(completed at the merge gate — see run continuation below)_

## Cost

* **Tokens:** not available to the agent in this session — the harness does not expose a token counter
  to the running agent, so no figure is stated rather than an invented one.
* **Wall-clock:** approximately 3h from session start to PR, dominated by test and coverage runs (each
  full-slice pytest pass is ~3.5 min; the two coverage passes are ~4 and ~5.5 min).
* **Population:** one Claude Code cloud session executing one `doc/plans/` plan end to end. ⛔ **This is
  NOT comparable to a plan-marshall `metrics.toon` total**, which counts an orchestrator-plus-agent
  dispatch tree under plan-marshall's own per-task billing boundary. This run has no such boundary and
  no dispatch tree, so the figures cannot be reconciled and no parity is implied.

## Contract check (Step 9)

_(completed as the final pre-merge commit — see run continuation below)_

## What have we learned (Step 9)

_(completed as the final pre-merge commit — see run continuation below)_

## Residue

Open, in the order a follow-up should take them:

1. **D2 in full — 54 modules over the 400-line budget.** The largest are
   `platform-runtime/test_claude_runtime.py` (4,667, ~40 classes — its classes are the cluster
   boundaries), `tools-script-executor/test_generate_executor.py` (3,106),
   `platform-runtime/test__claude_runtime_impl.py` (1,999), `tools-script-executor/test_execute_script.py`
   (1,808). This is the bulk of the plan's remaining work.
2. **D4 parametrization beyond the one landed family.** 223 families at ≥80% skeleton similarity,
   ~4,554 lines. Each needs reading — and `script-shared`'s matched positive/negative control pairs must
   be excluded by hand, since they scan as duplicates and are not.
3. **D3's B6 `parse_ns` sweep** — not started; and 17 remaining preamble findings whose paths do not
   terminate at a `scripts/` directory.
4. **The hermeticity check's missing arms.** `pytest-randomly` and `pytest-xdist` are absent here; the
   order-randomised and `-n auto` runs need an environment that has them.
5. **D4's cold read** (F6).
6. **The partition defect (F7)** — `test/pm-code-intelligence/` needs assigning to a plan by the epic
   owner. This run claimed it by operator decision, but that is a decision about *this run*, not a
   durable partition fix.
7. **Proposal to the epic (F5)** — set per-slice line floors from each slice's own composition.
