> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Reduce the runtime and script-substrate test slice

**Epic:** test-quality
**Branch prefix:** chore — maintenance-refactor-docs

> **Blocking dependency.** This plan may not start until plans `010` (test-authoring standards and
> enforcement) and `020` (shared test harness) have **landed on `main`**. Confirm both are present in
> your clone before D1 — `grep -n 'def parse_ns' test/conftest.py` and read the module-budget section
> of `marketplace/bundles/plan-marshall/skills/persona-module-tester/standards/testing-methodology.md`.
> If either is absent, **stop and report the run blocked**; do not invent a local substitute, because
> five sibling plans are converging on the same harness.
>
> **Read next.** `doc/plans/test-quality/README.md` — the epic's scoping brief, a git-tracked sibling
> in your clone. It carries the corpus census, the ten house-style rules **B1**–**B10** this plan
> applies, and the concurrency contract. The landed skills are the authority where they and the README
> disagree.

## Problem

The runtime and script-substrate slice — the platform runtime, the shared script library, the executor
generator, the extension API, the file/permission/validation tool surfaces, the provider store and the
logging surface — carries roughly 61,400 lines of `test_*.py` across fourteen directories.

This slice tests the layer everything else in the repository runs on, and its tests are correspondingly
careful. `script-shared/test_argparse_surface.py` builds a synthetic executor shim and drives real
`--help` probes through it; `platform-runtime/test_claude_runtime.py` redirects every filesystem root
before instantiating the runtime. That care is the right call and none of it should be undone.

What the slice pays for it is repetition of the redirect. `test_claude_runtime.py` declares an `rt`
fixture that monkeypatches three module-level roots — and then several of its ~40 test classes
re-declare `monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")` inside
**every individual test**, because the class needs the redirect without needing the runtime instance.
That line appears eight times in that module and sixteen more in its sibling. Corpus-wide the ratio of
`monkeypatch.setattr` calls to fixture declarations is roughly eleven to one, and this slice is where
that ratio is most visibly a missing class-scoped fixture rather than a genuine per-test need.

Alongside it sit the two costs the whole corpus carries: modules well over any reasonable budget
(`platform-runtime/test_claude_runtime.py` at ~4,680 lines and ~40 classes,
`tools-script-executor/test_generate_executor.py` at ~3,120), and docstrings that narrate the incident
rather than state the invariant.

One thing this slice has that no other does: it is the corpus's only genuine home for
**property-based testing**. The TOON parser, the identifier validators, the argparse-surface
derivation, the path normalisers under `tools-file-ops`, and the permission-string coercers are all
"for all valid inputs, P holds" contracts — exactly the domain **B8** reserves for Hypothesis. The
dependency is not present and adding it is a user-approval step, so this plan **names the call sites
and stops there**.

## Goal

The slice's isolation setup lives in fixtures at the scope that needs it, its modules are sized to
their behaviour clusters, its docstrings state invariants, and the operator has a derived, concrete
list of the places where property-based testing would actually earn its keep.

## Deliverables

Work the slice **largest module first**.

1. **D1 — Hoist repeated isolation setup into fixtures at the right scope** — apply **B4** across the
   slice. A `monkeypatch.setattr` (or `monkeypatch.setenv`) repeated in three or more tests of a class
   becomes a class-scoped or module-scoped fixture; repeated across three or more modules of a
   directory, it becomes a fixture in that directory's `_{domain}_fixtures.py`.
   `platform-runtime/test_claude_runtime.py`'s per-test `_SESSION_CACHE_BASE` redirect and
   `test__claude_runtime_impl.py`'s sixteen copies of it are the worked case. Do **not** convert any
   redirect into an `autouse` fixture with tree-wide scope: `persona-module-tester`
   § "Compose Isolation, Don't Impose It" governs that, and a blanket redirect of global resolution
   state collides with the tests that deliberately stage their own.
   *Done when:* no isolation call is repeated inline in three or more tests of the same class or
   module, every new fixture is explicitly requested rather than `autouse`, and the report carries the
   slice's `monkeypatch.setattr`-to-fixture ratio before and after.

2. **D2 — Split every module over the budget** — the module budget landed by plan `010`, split by
   behaviour cluster into `test_{unit}_{cluster}.py`. The slice's known over-budget modules include
   `platform-runtime/test_claude_runtime.py` (~4,680),
   `tools-script-executor/test_generate_executor.py` (~3,120),
   `platform-runtime/test__claude_runtime_impl.py` (~1,990),
   `tools-script-executor/test_execute_script.py` (~1,810),
   `script-shared/test_extension_base.py` (~1,360),
   `extension-api/test_extension_discovery.py` (~1,350),
   `manage-providers/test_providers_core.py` (~1,350) and `tools-file-ops/test_file_ops.py` (~1,320)
   — **re-derive the full list**, this one is a lead. `test_claude_runtime.py`'s ~40 test classes are
   already the cluster boundaries; use them rather than inventing new ones.
   *Done when:* every `test_*.py` in the slice is within the landed budget, each new module's name
   states its cluster, and every fixture a moved class depended on moved with it or into the
   directory's fixture module.

3. **D3 — Normalise preambles and argument construction** — apply **B6** and **B7** across the slice:
   `conftest.load_script_module` / `get_scripts_dir` for every module preamble, `020`'s `parse_ns` for
   every `argparse.Namespace`. Where `parse_ns` cannot serve a call site, leave the hand-built
   namespace and **record the call site in the report**.
   *Done when:* no `spec_from_file_location` or deep `Path(__file__).parent` chain remains in the
   slice, and every `parse_ns` exception is listed with its script.

   > **`test/plan-marshall/discovery_test_helpers.py` is NOT yours, despite sitting at the root of a
   > tree this plan works in.** It is an unprefixed helper module and it does need renaming — but its
   > only importers are `build-npm/test_npm_discover.py` and
   > `build-gradle/test_gradle_discover_modules.py`, both of which are in **plan `070`'s** slice.
   > Renaming it here would break two live imports in a concurrently-running sibling, which this plan's
   > own Out of scope forbids. Plan `070` § D1 owns the rename, alongside its analogous
   > `build_test_helpers.py` rename. Leave it alone.

4. **D4 — Parametrize the tabular cases and strip history from prose** — apply **B5** and **B3**. This
   slice's tabular families are the permission-string matrices, the notation-shape tables, the
   build-wrapper detection cases, and the extension-discovery filter cases. Collapse each into a
   parametrized table with an `ids=` list carrying what the per-test names said. Separately, strip
   plan ids, deliverable ids, PR numbers, lesson ids, and superseded-behaviour narration from test
   docstrings and comments, keeping present-tense rationale — and note that several docstrings in this
   slice legitimately explain **why a seam is patched the way it is** (the daemon-routing
   `__globals__` targeting, the `sys.modules` re-registration hazard). That rationale is present-tense
   and load-bearing; keep it.
   *Done when:* no family of three or more near-identical tabular tests remains, the `plugin-doctor`
   `test-docstring-historical-prose` rule reports zero findings over this slice, and both before/after
   counts are reported.

5. **D5 — Derive the property-based-testing candidate list** — a **report deliverable, not a code
   change**. Enumerate every unit in this slice whose contract is universal in the **B8** sense — text
   and format parsers, identifier validators, path normalisers, round-trip encoders — and for each
   record: the unit, the module that tests it today, the property that would be asserted, and the
   number of hand-picked example rows it currently uses. Candidates the review already saw include the
   shared `toon_parser`, `argparse_surface`'s derivation, the path handling under `tools-file-ops`, and
   the validators registered in `doctor-test-conventions.md` § "Rule 3 — Validator Registry" — that is
   a starting point, **not** the list. Derive the list; do not copy it.
   **Two sibling plans derive halves of the same list; coordinate rather than duplicate.** Plan `010`
   § D6 derives the whole-tree candidate list and lands **before** this plan — read its report and
   refine that list rather than starting from zero. Plan `080` § D4 derives the generator slice's
   candidates and may run concurrently with this one. Use the column set plan `010` fixed, and state
   in the report which rows are refinements of `010`'s and which are new, so the operator receives one
   list refined twice rather than three unrelated tables.
   *Done when:* the report carries the derived table with one row per candidate and its example-row
   count, states the total, and names its relationship to plan `010`'s whole-tree list.

6. **D6 — Report the measured deltas** — per-directory and slice-total line counts before and after;
   collected test count before and after; coverage before and after for the bundle paths the slice
   exercises; the `monkeypatch.setattr`-to-fixture ratio before and after; the `parse_ns` exception
   list; and the per-rule `test-conventions` finding counts.
   *Done when:* the report carries all six figures, each labelled with the command that produced it.

## Out of scope

* **Adding `hypothesis` to `pyproject.toml`, or writing a single property-based test.** Excluded
  because it is a third-party dependency and adding one is a user-approval step with no operator
  present. D5 produces the evidence the operator needs; plan `010` § D6 carries the standing proposal.
  A run that adds the dependency has taken a decision it was not authorised to take.
* **`test/conftest.py` and `test/_shared/**`.** Owned by plan `020` and consumed read-only here.
  Excluded because five sibling reduction plans run concurrently against the same harness. Note the
  slice's tests interact heavily with `conftest.py`'s autouse fixtures (`_plan_base_dir_sandbox`,
  `_credentials_dir_sandbox`, `_neutralize_daemon_routing`, `_root_fs_pollution_guard`) — **use them,
  do not change them**; a needed change is a proposal in the report.
* **Any file under `marketplace/bundles/**`.** Excluded because test refactoring that changes
  production code is not test refactoring. A production defect found while refactoring is **recorded**,
  not fixed.
* **Any test directory outside this plan's list.** Excluded because the neighbouring directory belongs
  to a concurrently-running sibling plan.
* **Weakening or removing the matched positive/negative control pairs.** `test/plan-marshall/script-shared/`
  carries deliberate matched pairs pinning the autouse neutralization fixtures — each arm is evidence
  only in contrast with the other, and their module docstrings say so. Excluded because a line target
  makes a "duplicate" of exactly the shape these pairs have, and deleting either arm silently voids the
  other's evidentiary value while leaving the suite green.

## Expected surface

Exactly these directories under `test/plan-marshall/`, and nothing else:

- `extension-api/`, `lsp-client/`, `manage-files/`, `manage-logging/`, `manage-providers/`,
  `platform-runtime/`, `ref-toon-format/`, `script-shared/`, `tools-file-ops/`,
  `tools-input-validation/`, `tools-permission-doctor/`, `tools-permission-fix/`,
  `tools-script-executor/`, `untrusted-ingestion/`

`test/plan-marshall/discovery_test_helpers.py` is **not** in this plan's surface — plan `070` owns its
rename, because plan `070` owns both of its importers (see the note under D3).

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The slice is ~61,400 lines across the fourteen listed directories | HYPOTHESIS | Re-derive with `wc -l` over the Expected surface list |
| `test_claude_runtime.py` is ~4,680 lines with ~40 test classes, and repeats the `_SESSION_CACHE_BASE` redirect per test in classes that could share a fixture | OBSERVED | the file; `grep -c '_SESSION_CACHE_BASE' test/plan-marshall/platform-runtime/test_claude_runtime.py test/plan-marshall/platform-runtime/test__claude_runtime_impl.py` |
| `discovery_test_helpers.py`'s only importers are under `build-npm/` and `build-gradle/`, both in plan `070`'s slice — so its rename is `070`'s, not this plan's | OBSERVED | `grep -rln 'discovery_test_helpers' test`; cross-check the two directories against plan `070` § Expected surface |
| `test/plan-marshall/script-shared/` carries matched positive/negative control pairs whose arms are evidence only in contrast | OBSERVED | the module docstrings of the daemon-routing and root-fs neutralization control modules under that directory |
| This slice contains units whose contract is universal in the **B8** sense | HYPOTHESIS — **D5 exists to settle it** | Derive from the slice itself. If the derivation finds few or none, that is the finding — report it, and say so plainly rather than padding the table. |
| No property-based test already exists anywhere in the tree | HYPOTHESIS — **asserted absence** | `grep -rn 'hypothesis\|@given\|strategies' test --include=*.py`. If one exists, D5's table starts from it rather than from zero. |
| The partition holds — every directory under `test/plan-marshall/*/`, every file at the root of `test/plan-marshall/`, and every top-level `test/` entry other than `plan-marshall/` itself (which the first two clauses already decompose) appears in exactly one of `030`–`080`'s Expected surface | HYPOTHESIS — **gating and halting; run it before D1** | List the directories and check each against the six plans' Expected-surface lists; `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time" states the procedure and the deliberate exclusions its table names (**read the table; do not assume a count** — it has grown since these plans landed). An entry in two lists, or in **none**, is a partition defect: **halt and report it**, do not claim or skip it unilaterally |
| Plans `010` and `020` have landed and their surfaces are present in this clone | HYPOTHESIS — **gating; this plan cannot start without it** | `grep -n 'def parse_ns' test/conftest.py`; the module-budget section of `persona-module-tester/standards/testing-methodology.md`. Absent → stop and report blocked. |

## Verification

> ⛔ **SUPERSEDED IN PART — read this before the three conditions below.** This plan landed carrying a
> three-part done-when whose third part is a **25% line floor**. That floor is **retired**, and so is
> every other per-slice floor in this epic: four executed plans returned between 0.52% and 2.56%
> against floors of 20–30%, and three of the six floors turned out to exceed their slice's entire
> comment-and-docstring volume. A run re-entering this plan holds the **five conditions** in
> `doc/plans/test-quality/README.md` § "What a reduction run must hold" — collected count, coverage,
> skipped count, wall-clock, and a line delta that is **measured and reported, never targeted**.
> Where that section and the text below disagree, **that section governs and the run reports the
> disagreement**. Everything else below — the per-deliverable checks, the cold read, the executable
> gate — stands unchanged.


**The three-part done-when as this plan landed. ⛔ Its third condition is RETIRED — read it as a
historical record, not as a gate.** Conditions 1 and 2 stand and are subsumed by the five in
`README.md` § "What a reduction run must hold", which also add the skipped count and the
wall-clock. **Condition 3 below is superseded**: the line delta is measured and reported, never
targeted, and no run is held to the 25% figure it names.

1. **Collected test count does not decrease.** Capture pytest's collected-item count for the slice
   before the first commit and again before the PR. Record both.
2. **Coverage does not decrease** for the bundle paths this slice exercises. Record before/after and
   the command.
3. ⛔ **RETIRED — recorded, not required.** **Line count drops by at least 25%** of the slice's starting total. If it cannot be reached without
   violating (1) or (2), **report the shortfall and stop**.

**A fourth check specific to this slice: the suite must stay hermetic.** This slice's tests are the
ones most able to become host-dependent, because they are the ones that redirect global resolution
state. After D1, run the slice twice — once normally and once under `-p no:randomly`-equivalent
ordering if available, and in both cases under `-n auto` — and confirm identical results. A fixture
hoisted to too broad a scope shows up as an order-dependent failure, not as a compile error.

**Executable.** `./pw verify` (the lane's build gate; this plan changes Python). Plus the
`plugin-doctor test-conventions` scope over each directory in the slice, before and after, with the
per-rule counts recorded. Use the invocation in
`doc/plans/test-quality/README.md` § "Running the plugin-doctor test-conventions scope" — a **bare**
call to `doctor-marketplace.py` fails with `ModuleNotFoundError: No module named '_dep_detection'`,
because the script has no `sys.path` bootstrap, so the invocation supplies the five scripts
directories it needs on `PYTHONPATH`. It is one command, touches no `.plan/`, and writes nothing. If
it cannot be made to run, report the affected measurement **unavailable** rather than substituting a
weaker check.

**By reading — cold read, required for D4.** D4 rewrites text whose value is what a later reader takes
from it, and the risk is not that too much history is removed but that the **invariant** is removed
along with it. Dispatch the lane's pre-PR verification sub-agent with **five rewritten test modules and
no other context** — not this plan, not the originals — and ask, for each of ten named tests: "What
contract does this test pin, and why does it matter?" A test whose rewritten docstring cannot answer
both has been over-stripped; restore the invariant (not the history) and re-read. Record the answers
verbatim.

**By reading.** For every fixture D1 introduces, confirm from the fixture's own definition that it is
explicitly requested rather than `autouse`, and that its scope is the narrowest that serves its
consumers. A module-scoped fixture used by one class is a scope error even though it passes; report
any you leave in place and why.

## Notes

* **Concurrency.** Plans `030` through `080` are mutually parallel by construction, each owning a
  disjoint slice. `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time"
  carries the full partition.
* **Order within the plan matters.** D1 before D2: hoisting fixtures shrinks modules and changes which
  ones are over budget, and a split done first strands fixtures away from the classes that need them.
* **This slice is the one to be conservative in.** It tests the substrate every other slice's subject
  runs on, and its isolation machinery is what keeps the whole suite hermetic. Where a reduction and a
  hermeticity guarantee conflict, the guarantee wins and the shortfall goes in the report.
