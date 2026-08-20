# Run report — 100-module-budget-campaign (run 01)

**Date (UTC):** 2026-08-19    **Branch:** `claude/module-budget-campaign-test-3gbpv6`    **PR:** _pending_    **Outcome:** _in progress_

> **Verification loop exit:** _pending_

**Slice taken:** run 1 — plan `050`'s slice, plan state and records.

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill: cloud-plan-lane` (project-local, `.claude/skills/`) |
| `pm-dev-python:pytest-testing` | `Read marketplace/bundles/pm-dev-python/skills/pytest-testing/SKILL.md` |
| `plan-marshall:persona-module-tester` § "Module Budget: 400 lines" | `Read marketplace/bundles/plan-marshall/skills/persona-module-tester/standards/testing-methodology.md` |

The `plan-marshall` plugin is not installed in this cloud session, so every bundle skill was read by
path. No skill named by the contract was unobtainable by both routes.

## Preconditions

**Blocking dependency — plans `010` and `020` landed.** Confirmed as the plan specifies:
`def parse_ns(` at `test/conftest.py:710`, and § "Module Budget: 400 lines" at
`marketplace/bundles/plan-marshall/skills/persona-module-tester/standards/testing-methodology.md:75`.

**Collision matrix — clear.** The epic README § "The collision matrix" names plan `100` in four rows:
`090`↔run 3, `090`↔run 6, `090`↔run 7, and `110`↔whichever slice `100` is running. This run takes
run 1, so only the `110` row applies. Neither `090`, `110` nor `120` has an open PR
(`list_pull_requests` returned three open PRs, all in other epics — #1308 review-apparatus, #1309
truthful-signals, #1312 cloud-plan-lane) or an in-flight branch (`git ls-remote --heads origin`
returned only `main`, `dist-claude`, this run's branch, and `claude/review-apparatus-analysis-mcf8md`).

## Deliverables

### D1 — Derive the current over-budget set, and halt if the partition does not hold

**Done.** The whole-tree sweep was run through the epic README's stated invocation, unmodified — the
five-directory `PYTHONPATH` prefix worked as documented, so no sixth directory was needed and the
next run inherits the invocation unchanged.

```text
PYTHONPATH=…plugin-doctor/scripts:…tools-marketplace-inventory/scripts:…tools-file-ops/scripts:\
…script-shared/scripts:…ref-toon-format/scripts \
python3 marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py \
  test-conventions --test-root test/
```

Whole-tree result: `total_issues: 633`, of which **`test-module-line-budget: 318`**.

Every one of the 318 findings was attributed by matching its path against the six reduction plans'
own **Expected surface** sections, read from those plans' own files, plus this plan's row 7. The
attribution is mechanical and re-runnable rather than eyeballed.

**The partition holds.** No module fell in two slices, and none fell in none.

| Run | Slice | Plan's lead | Derived | Δ |
|---|---|---:|---:|---:|
| 1 | `050` — plan state and records | 60 | **66** | +6 |
| 2 | `040` — delivery pipeline | 55 | 55 | 0 |
| 3 | `060` — runtime and script substrate | 53 | 53 | 0 |
| 4 | `030` — config and manifest | 39 | 40 | +1 |
| 5 | `070` — architecture and orchestration | 63 | 61 | −2 |
| 6 | `080` — plugin development and generator | 42 | 42 | 0 |
| 7 | plan `010`'s rule-test modules | 1 | 1 | 0 |
| | **sum** | **313** | **318** | **+5** |

66 + 55 + 53 + 40 + 61 + 42 + 1 = **318**, which is the whole-tree total with no residual bucket
beyond row 7 itself.

**Disagreement with the plan's own table, stated rather than absorbed.** The plan predicted that
*one* count would differ; **three** do, and the whole-tree total is 318 rather than the 313 the plan
and the epic README both carry. The direction is upward on balance (+5), which is what the epic
README's own "every number is a lead" caveat anticipates: modules cross the budget as sibling plans
land. Row 7 is confirmed at exactly one module, as the plan states, and it is claimed by no reduction
slice — by design, not as a defect.

The `+6` on this run's own slice matters most, since it sizes the run: 66 over-budget modules, not
60.

### D2 — Split this run's slice by behaviour cluster

**Partial**, and the verdict is stated as partial rather than narrated as complete, because D2's own
*Done when* is not met: "every module in the slice is within the budget **or is named in the report as
a single-class exception with its line count**". Three of the four modules still over budget are
single-class exceptions; the fourth is not, and § "Four modules remain over budget" below says why.
Everything else D2 asks for is done.

The file set was derived from the D1 attribution — the 66 modules the sweep named as over budget within
`050`'s Expected surface — never from a tree walk. An independent verification pass re-derived the
whole attribution against the six plans' own Expected surfaces and reproduced D1's table exactly.

⚠️ **The surface check this report originally reported was not a check.** It read: *"re-run whole-tree
after the split, every other slice's count is unchanged … a stray edit outside the surface would have
moved one of them."* That does not follow. `test-module-line-budget` is a threshold predicate — it
fires only above 400 lines (`_analyze_test_conventions.py:588`) — so an edit that does not carry a
module across the threshold moves no count anywhere. The invariance was real and told us nothing.
D2 asks for something else and stronger: *"Check the changed set after every edit, and report the
check."* Done properly, against `git diff --name-only`:

| Changed set, `origin/main...HEAD` under `test/` | Count | Inside `050`'s Expected surface? |
|---|---:|---|
| Modules the 66 sources became, at a new path | 142 | yes |
| `_{domain}_fixtures.py` created | 64 | yes |
| Sources still carrying their own name, rewritten in place | 57 | yes |
| Pre-existing in-budget slice modules edited for prose | **10** | **yes by directory, outside the letter** — see below |
| Anything outside the ten directories and three root prefixes | **0** | — |

The last row is the check that matters, and it is clean: nothing outside the surface was touched.

⚠️ **The 10 are a departure D2 does not license, and it is stated rather than absorbed.** D2 scopes the
work to "each over-budget module in the slice". These 10 were never over budget; they were edited
because they carried a prose reference the rename falsified, and leaving a false reference is what
§ Step 6 condition A forbids. So the run had two rules pointing opposite ways and chose truth over
scope. A reviewer entitled to disagree should know the trade was made: the alternative was ten comments
naming modules that no longer exist.

⚠️ **An earlier draft said 16, and 16 counted a different thing.** Sixteen in-budget modules were edited
*at some point during the run*; six were then restored to their `origin/main` content by a later pass
and are byte-identical at HEAD. The row's declared population is the changed set `origin/main...HEAD`,
in which the number is **10**. That draft also gave a false reason — "6 of the 16 sit outside the
slice's test modules or hold no clusters" — when all sixteen are `test_*.py` inside the slice and none
is a fixtures module.

66 modules become **199 test modules** plus **64 `_{domain}_fixtures.py`** modules. The slice held 209
test modules before and holds 342 now; **133 were never over budget and are byte-identical to
`origin/main`**, so 342 − 133 = 209 files carry this run's hand, of which 199 are what the 66 became and
10 are the in-budget modules whose prose was corrected (six more were edited mid-run and net out to no
change at HEAD — § D2's changed-set table). ⚠️ An earlier draft read "6 of the 16 above sit outside the
slice's test modules or hold no clusters" — the same false clause that § D2 corrects five paragraphs
above, restated here uncorrected because the figure re-derivation checked claims one at a time and
never read a paragraph against its neighbour. Of the 199, **142 sit at a path that did not exist before** and **57 carry
the name of the source they came from**. The `.py` file count goes 215 → 412.

**The 57 are the shape round 2 corrected, and they are the report's largest single change.** Ten of
them never lost their name; of those ten, **eight** were brought inside the budget by hoisting alone and
two — `test_list_stalled.py` and `test_restore_from_plan.py` — keep their name because a single class
over the budget cannot be split, and are still over budget (§ "Four modules remain over budget"). An
earlier draft said all ten were hoisting successes. The other **47 had their name given back**: see M14
below.

**Class boundaries are the cluster boundaries.** No class was split. Where a module carried loose
top-level `test_` functions, those are the clusters. Modules are named for the behaviour their clusters
share, never for position — the standard's own counter-example is `test_resolver_part2.py`, and the
run's first naming pass produced ten such names before the labeller was changed to walk more specific
candidates instead of appending an ordinal.

⚠️ **"Every module with test classes was split on them" was in this report and was false.** Four
over-budget sources carried several test classes and were **not** split at all — hoisting their
preamble alone brought them inside the budget:

| Source | Test classes | Lines, pre-split → now (`split('\n')`, one more than the rule's `splitlines()`) |
|---|---:|---|
| `test/plan-marshall/test_recipe_lesson_cleanup.py` | 3 | 557 → 306 |
| `test/plan-marshall/manage-lessons/test_remove.py` | 3 | 421 → 398 |
| `test/plan-marshall/plan-retrospective/test_recall_read_intent_denominator.py` | 5 | 419 → 372 |
| `test/plan-marshall/test_lessons_capture_workflow.py` | 7 | 403 → 382 |

Two things follow, and the report states both rather than the flattering one. The *outcome* D2 wants —
budget compliance without splitting a class — is met. The *method* it prescribes is not: D2 says split
an over-budget module on its class boundaries, and these four were not. And because each produced
exactly one module, their hoist rests on a clause whose precondition does not hold — D2 licenses moving
helpers "that **more than one resulting module** needs", and § Out of scope excludes "hoisting fixtures"
as belonging to the slice's own reduction plan. ⚠️ **And the precondition fails for more than these four.** D2's clause turns on the number of
*resulting modules*, not on how many classes a source had, and **nine** sources produced exactly one
module plus a `_{domain}_fixtures.py`: the four named, plus `test_list_stalled.py`,
`test_phase_boundary_inline.py`, `test_planning_lane_corroboration.py`,
`test_planning_lane_request_body.py` and `test_plan_efficiency_anchors.py`. An earlier draft scoped the
confession to four and called the residue bounded on that basis. **A follow-up that splits these on
their class boundaries would bring both the method and the hoist inside the letter.** This run does not, and the
reason is scope rather than merit: the four are inside the budget, their names are true, and re-running
the emitter over them would re-open every measurement in this report for no change the rule can see.

**Four modules remain over budget**, and they are two different things. The plan's stated exception is
"a class larger than the budget", so they are reported split by whether the class actually is. The line
counts are the doctor's own, from the final sweep:

| Class | Class lines | Module lines | Over budget alone? | Now in |
|---|---:|---:|---|---|
| `TestDispatchBoundaryContextLoadColumns` | **495** | 536 | **yes** — the plan's exception | `plan-retrospective/test_analyze_logs_dispatch_boundary_context_load_columns.py` |
| `TestCmdListStalled` | **424** | 466 | **yes** | `manage-lessons/test_list_stalled.py` |
| `TestCmdRestoreFromPlan` | **422** | 465 | **yes** | `manage-lessons/test_restore_from_plan.py` |
| `TestPhase5LoggingGapExtractors` | 399 | 417 | **no** — the class fits, by one line | `plan-retrospective/test_analyze_logs_phase5_logging_gap_extractors.py` |

The plan records exactly one budget-exceeding class for the `060` slice and labels the count HYPOTHESIS
for every other slice. For `050` it is **three**.

**The bound on those three is a plan constraint, not irreducibility, and the difference matters to
whoever owns the flip to `error`.** `TestCmdListStalled` (18 methods, no class-level state),
`TestCmdRestoreFromPlan` (14, none) and `TestDispatchBoundaryContextLoadColumns` (14 methods, two
constants, one helper) are each mechanically separable into two classes over two modules. What stops
this run is the plan's own sentence — *"A class larger than the budget is a stated exception, **not a
licence to split a class**"* — and § Out of scope's exclusion of namespace conversion. Read as
"these cannot be made smaller", the row would be false; read as "this plan may not be the one that
does it", it is exact.

⚠️ **Two of these four are modules that kept their own name, so "the modules that kept their name are
the ones hoisting brought inside the budget" — which this report said — is false of them.**
`test_list_stalled.py` fell 495 → 466 and `test_restore_from_plan.py` went 464 → **465**: it grew by a
line. (Both pairs use `splitlines()`, the method the rule itself uses at
`_analyze_test_conventions.py:587`. An earlier draft paired one method's "before" with the other's
"after", giving 465 → 466 for a file the table just above lists at 465.) Both keep their name because a single class over the budget cannot be split, not because
hoisting succeeded. Ten sources kept their name; **eight** of the ten are inside the budget.

The fourth is a distinct shape the plan does not name, and this report does not fold it into the
exception: the class is inside the budget and the *module* is not, because a module also carries a
header, an import block and a banner comment. `TestPhase5LoggingGapExtractors` is 399 lines in a
417-line module. An earlier draft called the remaining 18 lines "verified irreducible, with no slack
left to find", and that was not true of the file — `test_analyze_logs_phase5_logging_gap_extractors.py:14-16`
is a three-line decorative banner restating what the class docstring at `:20` already says, and the
standard's own first Fundamental Principle is "no zero-benefit comments".

⚠️ **Its replacement argument was no better, and round 5 named why.** That draft then reasoned: *"a
399-line class leaves room for exactly one non-class line, and no header, licence and import block can
be one line."* True, and an answer to a question nobody asked. The live question is why the **class**
is not split, since at 399 lines it is inside the budget and the plan's stated exception — which is
about a class *larger* than the budget — does not reach it. The class is a flat container of five
banner-separated behaviour groups (`pair_outcome_emissions`, `cluster_dispatches`,
`detect_outcome_for_diffed_tasks`, `read_dispatch_boundaries_per_phase`, `cmd_run`), and splitting it
is mechanically easy.

**The real reason, which is checkable rather than constructed:** a test's namespace is its class, so
splitting one test class into two is *converting namespaces* — named verbatim in § Out of scope and
assigned there to "the slice's own reduction plan". It would also change the `Class::test` identity of
every test it moved, and that multiset is the evidence every other claim in this report rests on (§ D4:
3974 before, 3974 after, 0 lost, 0 gained). So this module is **residue with a named owner**, not an
instance of the plan's exception, and the report says so rather than dressing it as irreducible.

⚠️ **A fifth module was on this list and should not have been.**
`test_manage_locks_merge_lock_live_worktree_reclaim_guard.py` stood at 432 lines around a 355-line
class, and the justification given for leaving it was that its pytest fixtures could not be hoisted
because `F811` is reported at the consuming parameter, out of reach of any `noqa` on the import. **That
was false.** A module-level `# ruff: noqa: F811` does reach it, and
`test/plan-marshall/plan-marshall/test_phase_handshake_phase_steps.py:3` had been using exactly that
pattern all along. The claim was never checked against the tree; an independent verification pass
found it. Hoisting those fixtures brings the module to **387 lines**, inside the budget.

**Deviation from D2's letter, stated rather than absorbed.** D2 says shared helpers, constants and
loaders "move into a `_{domain}_fixtures.py`". This run hoists **per source module**
(`_ledger_reconciliation_fixtures.py`), not per directory. `manage-metrics/` alone holds **9**
over-budget modules whose preambles bind the same names to different values (an earlier draft said 13); merging them into one
`_manage_metrics_fixtures.py` — which already exists, with its own contents — would have required
renaming references across the directory, which is a semantic edit, not a move. That reason stands on
its own. `unique-fixture-basenames` and `test-helper-module-misnamed` both remain at 0, so the naming
satisfies the enforced rules.

⚠️ **A second reason was given here and it argued against the wrong alternative.** It read: *"per-source
hoisting also keeps each script load executing once rather than once per output, which is the mechanism
the epic names as most likely to make this campaign the one that slows the suite."* The alternative
under discussion is per-**directory** hoisting, and `conftest.load_script_module` re-executes the script
on every call rather than caching it — so per-directory hoisting would load *fewer* times, not more.
Against the alternative actually being rejected, this reason points the other way. It is true only
against *no* hoisting at all, which nobody proposed. The clause is removed rather than repaired.

**One `@pytest.fixture` exception to the hoist, and its cost is stated.** A fixture stays in the modules
that consume it. Moving one to the fixtures module and importing it costs two suppressions: `F401` on
the import, because a fixture is never used *as* a name, and a module-level `# ruff: noqa: F811` for
every test that takes it as a parameter — F811 is reported at the parameter, out of reach of a `noqa`
on the import, so only a module-level directive reaches it. That directive disables the check for a
whole module, which is a real cost, so it is paid only where keeping the fixture inline would push a
module past the budget. **Exactly one module qualifies** (above).

Everywhere else the fixture is duplicated into the outputs that consume it, closed over
fixture-to-fixture dependencies. **The magnitude, measured with the whole slice on both sides of the
comparison** — an earlier draft put the 66 sources on the before side and the whole slice on the
after side, which is not a comparison: the slice's module-level `@pytest.fixture` definitions go from
**40 to 101**. Before the split, 9 names were defined in more than one file, for 19 extra copies; now
12 names are, for 80. **This run therefore added 61 extra copies.**

⚠️ **"Every copy is byte-identical today, so nothing has diverged" was in this report and is false.**
Nine fixture names carry more than one distinct body text: `_seed_guarded_plan_dirs` (6 variants across
28 files), `isolated_base` (4), `_stubbed_invariants` (3), `_stub_metadata` (3), and `adr_dir`, `env`,
`_stub_title_tokens`, `_stub_resolver_seam`, `_build_is_necessary` (2 each).

**What this run is and is not responsible for, measured rather than asserted.** Hashing every
fixture-decorated function with its docstring stripped, at `origin/main` and at HEAD: **zero bodies
exist at HEAD that did not exist on main.** The split multiplied copies — 8 → 28, 4 → 19, 2 → 11 — and
introduced no new variant; eight of the nine names already carried more than one body on main. The
ninth is this run's and it is a docstring: correcting the 19 false `_register_unseeded` sentences (M24)
took `_seed_guarded_plan_dirs` from five body *texts* to six while leaving its five *behaviours*
untouched. So the divergence a reviewer will find is pre-existing; what this run adds is more places for
a future edit to diverge, and that is the drift surface priced here.

⚠️ **The split also moved 10,645 lines into files the budget rule does not measure, and the −62 should
be read knowing that.** `test-module-line-budget` only inspects modules pytest would collect —
`_is_collected_module` in `_analyze_test_conventions.py:554` matches `test_*.py` and `*_test.py` and
nothing else — so a `_{domain}_fixtures.py` is invisible to it however long it grows. The slice's
helper modules go from **6 files / 1,572 lines** to **70 files / 12,217 lines** — the same population
counted on both sides, which an earlier draft did not do: it dropped `_lessons_helpers.py` and
`plan-retrospective/__init__.py` from the after side while counting them on the before side, and
reported 68 files / 12,118 lines. Three now exceed 400
lines, and one of those is not this run's:

| Helper module | Lines | Whose |
|---|---:|---|
| `manage-metrics/_manage_metrics_module_fixtures.py` | 730 | **this run's** |
| `audit-archived-plan-retrospectives/_audit_fixtures.py` | 664 | pre-existing — 664 lines at `9180606~1` too |
| `manage-metrics/_record_model_representability_fixtures.py` | 572 | **this run's** |

**Seventeen** of the 62 modules brought inside the budget therefore bought part of that with a helper
the rule cannot see: `_manage_metrics_module_fixtures.py` (730 lines) serves 15 modules and
`_record_model_representability_fixtures.py` (572) serves 2. An earlier draft said "two", which counted
the oversized helpers rather than the modules drawing relief from them. This is not a rule evasion — the standard's subject is a *test module*, and a file holding
no tests is not one — but a reader entitled to think "62 modules got smaller" is entitled to know
where the lines went, so it is stated rather than left to the diff.

### D3 — Preserve every shared registration through the move

**Done, and the answer is the strong one: this run changed no registration name at all.**

Every `load_script_module` / `spec_from_file_location` call moved **whole** into its module's fixtures
module, carrying its own registration name with it. No two previously-distinct registrations were
collapsed onto a shared one, which is the mechanism that cost plan `030` 173 order-dependent failures.
The report therefore names **no** registration whose name this run changed, and the "demonstrably free
of module-level mutable state" evidence the plan asks for alongside such a change is not owed, because
no such change was made.

**Measured, with the whole slice on both sides**, at `9180606~1` and now. A registration's key is the
explicit `module_name` where one is passed, the script stem otherwise (`load_script_module`'s
documented default), and the first argument of a direct `spec_from_file_location`:

| | `9180606~1` | now |
|---|---:|---:|
| Registration call sites in the slice | 163 | 163 |
| Distinct `sys.modules` keys | 137 | 137 |
| Keys lost | — | **0** |
| Keys gained | — | **0** |
| Keys registered from **more files** than before | — | **0** |

⚠️ **The call-site count depends on how a call is recognised, and an independent re-derivation got
172 on both sides rather than 163.** The invariant — equal on both sides, 0 lost, 0 gained, 0 keys
registered from more files — reproduces under either counting, and the 137 distinct keys reproduce
exactly. The 163 here counts calls whose registration key is a string literal the regex can read; the
172 counts every syntactic call site including three whose key is built from an expression. Neither is
wrong; the report states which it used because a bare 163 is not reproducible without it.

The last row is the one that matters, and it is the check M11 was found by. Identical key counts would
still permit the M11 defect — the same key registered from three files instead of one, handing siblings
three distinct module objects racing one name — because that changes no key, only how many files write
it. Counting registering *files* per key is what excludes it, and no key in the slice is written from
more files than it was before the split.

Order-independence was checked as the plan specifies — the slice in default directory order and again
with the directories reversed:

| Order | Result |
|---|---|
| Default | 4207 passed in 186.14s |
| Reverse directory order | 4207 passed in 176.45s |

### D4 — Prove the split moved text, not meaning

**Done, and the checks are built against the specific failure the plan names.** Plan `050` sliced
between `node.lineno` and `node.end_lineno` — exact for every construct the AST models — and dropped
162 column-0 comments, because the AST does not contain a comment.

So this split partitions each source over **lines**, not nodes: a construct's region runs from the line
after the previous construct's `end_lineno` through its own, which sweeps up the decorators, the
leading comments and the blank lines ahead of it. The union of the header and the regions is the whole
file, asserted per module before anything is written — a gap or an overlap raises rather than emitting.

Comments are diffed **as their own dimension** and as a **multiset**, so a comment that vanished cannot
be masked by one that was duplicated. Measured against the pre-split sources over the eleven affected
directories:

Two populations are in play and the report names which is which, because they are close enough in
size to be mistaken for one another. **Population P1** is every `.py` sitting directly in the eleven
affected directories — the `_{domain}_fixtures.py` modules included, since the text this run moved
landed in them. ⚠️ An earlier draft defined P1 as `test_*.py` only, and that definition does not produce
the table's own numbers: `test_*.py` alone gives 8052 comments and 65751 code lines on main, not 8221
and 67933. The `Class::test` row is the exception and is measured over `test_*.py` alone (all-`.py`
gives 3990, not 3974), because a fixtures module holds no tests. One label had covered two populations
in three rows of a single table; each row now names its own. **Population P2** is the
whole slice as § Expected surface defines it — the ten directories recursively plus the three
root-level modules — which is what the deltas in D5 count.

**The before side is `origin/main` as it stands, not merely the pre-split commit** — and those turn out
to be the same tree for this slice. `git diff 9180606~1 origin/main` over the ten directories and the
three root prefixes returns **zero files**, so main's three intervening commits touched nothing here and
every figure below is a comparison against the current base, not a stale one.

| Measure | Population | `origin/main` | HEAD | Verdict |
|---|---|---:|---:|---|
| Comment texts | P1 | 8221 | 8690 | **27 distinct absent, 0 unexplained** (below) |
| `Class::test` occurrences | P1 | 3974 | 3974 | **0 lost, 0 gained** |
| Non-blank non-comment lines | P1 | 67933 | 71555 | **100 distinct absent, 0 unexplained** (below) |
| Collected items | P2 | 4207 | 4207 | identical |
| Distinct `Class::test` ids | P2 | 3822 | 3822 | identical |

⚠️ **P1's 3974 is not the 3970 an earlier draft carried, and the difference is not this run's.** P1
covers the eleven directories whole, and `origin/main` added four tests to
`test/plan-marshall/test_lane_refactor_cleanup_sweep.py`, which sits in one of them and which this run
never touched. Measured against the pre-split commit the branch reads `lost=0 gained=4`; measured
against current main it reads **`lost=0 gained=0`**. The second is the honest one, and it is why the
comparison was re-taken after the merge rather than carried forward.

⚠️ **"Nothing lost" stopped being the right measurement once this run began deliberately rewriting
prose.** 27 comment texts and 100 code lines present on main are absent at HEAD. A bare count there is
not evidence either way, so each absence is **classified**, and the number that means a text was lost is
the residue:

| Why a text is absent at HEAD | Comments | Code lines |
|---|---:|---:|
| A directional reference this run deliberately rewrote (M2, M13) | 22 | 12 |
| A round-2 prose correction (M16–M21) | 0 | 21 |
| The docstring reframe moved the opening `"""` — the text survives verbatim one line down (M10) | 0 | 43 |
| A reference repointed onto the successor glob — `test_add.py` → `test_add*.py` | 5 | 17 |
| `ruff --fix` rewrote an import whose names the split left partly unused | 0 | 7 |
| **UNEXPLAINED** | **0** | **0** |

The round-2 row is not a hand-written declaration. Those corrections were applied by several small
passes rather than one table, so their removed lines are read from the diff itself
(`git diff -M -U0 HEAD -- test/`) — a hand-declared list would be a second chance to mis-state what was
changed, which is the defect this whole check exists to catch.

**Every difference accounted for.** The comment count *rises* by 469 across the slice: an output module
carries its source's import statements, so a comment on an import line is replicated once per output.
An earlier pass rose by 719, and the extra was the comment *blocks* between imports being replicated
too — which also multiplied one `test-docstring-historical-prose` finding into three (M8). Output
modules now take the import statements alone and the commented block survives whole in the fixtures
module.

⚠️ **This check is the only reason M4 was caught.** Seven tests were silently lost to a filename
collision, and every other signal was green: the suite passed, the doctor sweep reported the budget
falling, ruff and mypy were clean. Only the multiset diff against the pre-split sources said
`tests lost=7`. A run that had asserted "the split is a pure move" on the strength of a green suite
would have shipped it.

Seven import lines no longer appear verbatim: `ruff --fix` rewrote them where the split left some of
their names unused (`from conftest import get_script_path, load_script_module, run_script` becoming the
subset each module needs). Every name they bound still resolves — checked statically across all 263
rendered modules (199 outputs + 64 fixtures modules) before writing, and again by the suite.

### D5 — Report the measured deltas

Every figure with the command that produced it. `{DOCTOR}` is the epic README's
`PYTHONPATH`-prefixed `doctor-marketplace.py test-conventions` invocation, used unmodified — the five
directories it names were sufficient, so the next run inherits it unchanged.

| Measure | Before | After | Δ | Command |
|---|---:|---:|---:|---|
**Both sides are measured at `origin/main` and at HEAD**, not against the pre-split commit — the base
moved three commits during the run and the whole-tree figures move with it.

| Measure | `origin/main` | HEAD | Δ | Command |
|---|---:|---:|---:|---|
| `test-module-line-budget`, slice `050` | 66 | **4** | −62 | `{DOCTOR} --test-root test/`, grouped by slice |
| `test-module-line-budget`, whole tree | **321** | **259** | −62 | `{DOCTOR} --test-root test/` |
| `total_issues`, whole tree | 640 | 578 | −62 | same |
| `test-module-preamble-boilerplate`, whole tree | 104 | 104 | **0 net, 30 gained / 30 lost** | same, decomposed per file |
| `test-docstring-historical-prose`, whole tree | 200 | 200 | 0 | same |
| `subprocess-pythonpath`, whole tree | 15 | 15 | 0 | same |
| `unique-fixture-basenames` / `test-helper-module-misnamed` / `identifier-validator-corpus` | 0 | 0 | 0 | same |
| Test modules in slice | 209 | 342 | +133 | `Path.rglob('*.py')` over the slice, `test_*` only |
| `.py` files in slice | 215 | 412 | +197 | same, all `.py` |
| Helper-module files in slice | 6 | 70 | +64 | same, non-`test_*` only — **not measured by the rule** |
| Helper-module lines in slice | 1572 | 12217 | +10645 | the same population on both sides |
| Collected items, slice | 4207 | 4207 | 0 | `uv run python -m pytest {slice} -o addopts= --collect-only -q` |
| Distinct `Class::test` ids, slice | 3822 | 3822 | 0 | `ast`, class/function walk |
| `@pytest.fixture` definitions, slice | 40 | 101 | +61 | `ast`, decorator walk — **all** fixtures, not only module-level; strictly module-level it is 38 → 99, and the +61 delta is identical either way |
| Comments in slice | 7967 | 8750 | +783 | `tokenize`, `COMMENT` tokens |
| Lines in slice | 90928 | 97476 | **+6548 (+7.2%)** | `len(read_text().split('\n'))` |
| Coverage, slice bundle paths | 89% | 89% | 0 | see the command below |

⚠️ **The whole-tree count is 321 on main, not the 318 D1 derived, and the three extra are not this
run's**: `test/marketplace/targets/test_component_targets.py`,
`test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py` and
`test/pm-plugin-development/plugin-doctor/test_analyze_target_scope.py`, all outside the slice. (An
earlier draft wrote "the four extra" against a difference of three.) The slice itself is byte-identical
across main's three intervening commits (§ D4), so the −62 is the same 62 modules whichever base it is
measured against, and the other six rules land on **exactly** their main-side values.

⚠️ **A net zero is not the statement it looks like, and an earlier draft leaned on it as if it were.**
That draft read: *"a split that quietly created a new preamble-boilerplate or historical-prose finding
would show there."* It would not. `test-module-preamble-boilerplate` is 104 on both sides, and the
per-file multiset difference is **30 gained and 30 lost** — 26 of the gains are in `_*_fixtures.py`
modules this run created, which is precisely the migration the hoist performs. The aggregate hid it
completely. **The decomposition is the evidence; the net is not** — and this is the second time in this
report an equality was mistaken for a check, the first being D2's threshold-predicate surface check
(M23).

**The coverage command in full**, because an earlier draft named only "{10 skill script dirs}" and was
not reproducible as written. `{B}` is `marketplace/bundles/plan-marshall/skills`:

```bash
uv run python -m pytest {slice} -o addopts= -q -p no:randomly \
  --cov={B}/audit-archived-plan-retrospectives --cov={B}/manage-adr \
  --cov={B}/manage-change-ledger --cov={B}/manage-findings --cov={B}/manage-lessons \
  --cov={B}/manage-locks --cov={B}/manage-metrics --cov={B}/manage-status \
  --cov={B}/manage-tasks --cov={B}/plan-retrospective --cov-report=term
```

**The line delta is an observation, not a target.** +6.8% **confirms** the plan's HYPOTHESIS that
splitting is line-neutral to slightly positive; it is not a refutation, and nothing was deleted to
improve it. The growth is a header and an import block per new module, which is the cost the plan
predicted and priced in when it refused a line floor.

It was **+9.7%** before the docstring change described under M1: replicating each source's whole
docstring into every output was the single largest contributor, and keeping the full text once in the
fixtures module removed about 2,700 lines while making each output's docstring true of that output.
The number moved because a defect was fixed, not because it was chased. It then rose again, from
+6.6% to +6.8%, when the clusters were regrouped by theme (M14): a theme group that will not fit the
budget is cut into more bins than an adjacency packing needed, and each extra bin costs another header
and import block. That is the price of the names being true, stated rather than absorbed.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty — this run changes Python — so the
full gate applies.

_verify pending_

## Findings

One row per instance. "Move-induced" means this run's split created it; "pre-existing" means the
split moved byte-identical text and the defect was already there.

### Move-induced, all fixed

| # | Finding | Evidence | Disposition |
|---|---|---|---|
| M1 | A replicated module docstring enumerates the contract of the **original** module, so in each output it claims coverage that output does not have. `test_build_queue_admission.py` claimed corrupt-file handling, machine-global resolution, foreign-holder pruning and a spawned-subprocess contention suite — none of them in it | Cold read § "docstrings describing what the code does not do" | **Fixed** — each output keeps the docstring's summary paragraph; the full text lives once in the fixtures module beside it |
| M2 | 29 directional references falsified across 19 files: a comment reading "the test below" was true while helper and tests shared a module, and points at nothing once the helper is hoisted | Cold read items 4–6; sweep of the 64 new fixtures modules | **Fixed** — each rewrite drops the direction and keeps the claim. Directional words still true (a markdown heading's body, a magnitude, a numeric threshold, a symbol genuinely above in the same file) were checked individually and kept |
| M3 | Module names truncated to a character budget, ending mid-phrase — `_is_absent_rather_than`, `_stale_legacy_key_without`, `_does_not_claim`. 71 of the generated names exceeded 52 characters | Name sweep of the generated set | **Partly fixed, and the residue is named rather than claimed away.** Candidates are built from whole meaningful words and a name repeating the unit it already carries has the repetition dropped. **24 of the 206 new stems still exceed 52 characters** (longest 72, `test_pre_commit_verify_freshness_unresolvable_worktree_falls_back_to_cwd`), measured on the stem without the `.py`. ⚠️ An earlier draft added "none is truncated"; that was false — `test_manage_metrics_reconcile_accumulator_into.py` comes from `TestReconcileAccumulatorIntoPhase` and `test_registered_aspects_render_dispatched_aspects_have.py` from `TestDispatchedAspectsHaveStaticRow`, both cut mid-phrase. **Round-2 contract lens, finding 7.** The truncation is now on whole words rather than characters, which is what removed the `_is_absent_rather_than` shape, but a whole-word cut can still land mid-phrase and several did |
| M4 | **Seven tests silently lost.** Two bins of one module resolved to the same filename; `render()` keys its output by filename, so the second write replaced the first and every test in the first disappeared | `verify_move.py` reported `tests lost=7`, all from `test_manage_locks_merge_lock.py` (`TestIdempotentRepoll`, `TestReleaseAdvancesFront`) | **Fixed** — the name search widens until unique, and a duplicate is now an assertion rather than a silent overwrite |
| M5 | The fixtures module grouped every import ahead of every statement, moving a `sys.path.insert` **after** the import it enables | Cold read item 3 | **Fixed** — regions are emitted in source order, imports and statements interleaved |
| M6 | A compacted docstring was cut at its first physical **line**; these docstrings wrap, so the module's own description ended mid-sentence (`…the first-class`) | Scan for docstrings not ending in terminal punctuation | **Fixed** — compaction keeps the summary **paragraph** |
| M7 | `test-module-preamble-boilerplate` rose 100 → 102: two modules whose shared preamble sat just under the hoisting threshold duplicated a `spec_from_file_location` block into each output | Whole-tree sweep diff | **Fixed** — threshold lowered so the loader lands in a fixtures module, as D2 directs. Back to the **main-side 104**; the "back to 100" an earlier draft carried was the pre-split baseline, which main has since moved |
| M8 | `test-docstring-historical-prose` rose 200 → 203: comment blocks *between imports* were replicated into every output, multiplying a citation | Whole-tree sweep diff, per-file | **Fixed** — outputs take import statements only; the commented block survives whole in the fixtures module |
| M9 | `test-docstring-historical-prose` rose 200 → 201: a **non-splitting** module keeps its own full docstring, and the fixtures module copied it, duplicating the citation it carries | Whole-tree sweep diff, `manage-status` 2 → 3 | **Fixed** — the fixtures module carries the full docstring only when the outputs are compacted |
| M10 | M1's fix **relocated** the over-claim rather than removing it: the inherited docstring now heads a fixtures module, which contains no tests, while still opening "Tests for ``x.py``" and enumerating a contract. The second cold read called it "the largest over-claim", listing six contract bullets whose tests are in sibling modules | Second cold read, Q2 | **Fixed** — the inherited text is *framed*, not edited: a lead-in states what the file is and whose contract the text below pins, and the original prose follows unchanged |
| M11 | A preamble too small to hoist was **duplicated** into each output — and where it loads a script, that registers the same `sys.modules` key from three files and hands the siblings three distinct module objects racing one name. `compile-report`'s `cr_behavior_mod` had one registration on `main` and three after the split | Independent verification pass, trap 2 follow-through | **Fixed** — a preamble that loads a script is hoisted whatever its size. One registration again |
| M12 | D2's stated reason for keeping every fixture inline — that `F811` "is reported at the parameter, so no `noqa` on the import can reach it" — is **false**. A module-level `# ruff: noqa: F811` reaches it, and this repo already uses that pattern. The false claim was the justification for leaving a module over budget | Independent verification pass; `test_phase_handshake_phase_steps.py:3` | **Fixed** — the claim is corrected and the module hoists its fixtures, falling 432 → 387 lines |
| M13 | The M2 sweep missed five instances of its own defect class: comments reading "the autouse fixture below" in fixtures modules that hold no fixture at all | Independent verification pass, finding D | **Fixed** — **36 directional references now corrected across 21 files**, up from 29 across 19. ⚠️ The headline's "five instances" and 29 → 36 do not reconcile — 29 + 5 = 34; the sweep the finding triggered corrected seven, of which five are the instances it named |
| M14 | **Bins were packed by ADJACENCY, so a module's name was true of its leading cluster and of nothing else.** `test_ledger_reconciliation_manifest_parsing.py` held one manifest-parsing test in ten; `test_compile_report_fault_paths.py` ended with a registry-consistency guard that is not a fault path. An earlier draft of this report disclosed this as "the naming rule's limit" and declined to fix it — that was a decision to ship a false name, not a limit | Round-1 verification, naming lens; `name_truth.py` measuring the share of a module's tests whose own cluster name contains the label the filename claims | **Fixed** — clusters are regrouped by shared theme before packing, the theme key deepened only where a group will not fit the budget, and a group that still will not fit is chunked. Modules whose name covers under half their tests fall **107 → 65** of 189; sibling names where one is a strict prefix of another fall **30 → 19** |
| M15 | With bins regrouped, two bins of one source could resolve to names one word apart — a distinction the name does not actually draw, and the M4 collision hazard's near neighbour | Round-1 verification; `check_names.py` | **Partly fixed, and M16 re-created it.** The emitter still rejects a candidate whose sibling extends it by a single word, and a duplicate output name is still a hard assertion rather than an overwrite. But handing 47 sources their bare unit name back put `test_build_queue` beside `test_build_queue_admission`, `test_manage_metrics_phase_boundary` beside `…_phase`, `test_orchestrator_store` beside `test_orchestrator_store_orchestrator`: **37 same-directory sibling pairs now differ by exactly one word**, up from the 0 M15 left. Round 4 found this; the report had discussed only the generic 141-prefix-pair trade and not the specific hazard M15 exists to remove |

### Round 2 — move-induced, all fixed

| # | Finding | Evidence | Disposition |
|---|---|---|---|
| M16 | ⭐ **M14's fix left 65 of 189 names still false, and this report had argued no true name existed.** It read: *"a module whose clusters share no theme has no true name short of listing them, and the standard asks for a name rather than a list."* The premise generalised one labeller's failure into an impossibility. A bin whose clusters share no theme is *the rest of unit X*, and `test_{unit}.py` names exactly that while claiming no cluster at all — and every one of the 47 units was **free**, because the split had renamed its source away | Round-2 contract lens, finding 6; verified by testing all 47 candidate names for collision | **Fixed** — the bin whose label is most false in each unit gets the source's name back. Measured over the 199 modules the 66 became: **58 now carry the unit name and make no cluster claim**; of the 141 that carry a label, **18 are true of under half their tests, down from 65**. ⚠️ An earlier draft said 47 / 57 / 142: the run's own next commit (`2e2b7d0`) restored a 48th source name, and the disposition was not re-derived after it — the same "a later commit re-staled it" shape as M26 |
| M17 | Four `test_add_*` modules each claim to cover "the ``_allocate_and_write_scaffold`` helper that both subcommands share". None of the four touches it; the tests that do are in a fifth module. In two of the four that false bullet was the **whole** `Covers:` list, so the docstring described none of the file's content. The splitter had deleted the line naming the class it moved away and fused the two halves, leaving a sentence with no subject | Round-2 prose lens, finding 3 | **Fixed by rule, not by hand** — a `Covers:` bullet naming a **test class** absent from the file is dropped whole; where nothing true remains the heading goes too. The sweep over all 206 created modules found exactly four. ⚠️ An earlier draft stated the criterion as "a symbol absent from the file's **code**", which is not what ran: under that reading `test_add_collision_safe_allocation.py:11` also names `_allocate_and_write_scaffold`, which appears in that file only inside comments. The bullet is true there, so the outcome stands — but the stated rule was not the applied rule |
| M18 | `test_planning_lane_request_body.py:63` states *"the helpers below are local to this module"* while importing all nine of them from `_planning_lane_request_body_fixtures.py`; `:23` and `:37` say "the fixtures below" of fixtures no longer below | Round-2 prose lens, findings 1–2 | **Fixed** — the sentence now says where the helpers are and that nothing is shared |
| M19 | `_lessons_crud_fixtures.py:11` says *"This module absorbs the four single-verb suites whose bodies were each small enough that a dedicated file cost more navigation than it bought"* — in a preamble holding no tests, about suites that now have dedicated files, written by the run that gave them those files | Round-2 prose lens, finding 4 | **Fixed** — the subject is the four modules the preamble serves, and the load-once mechanism sentence (which still holds) keeps its claim |
| M20 | Six fixtures-module docstrings take the file itself as grammatical subject — *"This module drives it"*, *"Each test here pins"*, *"This file pins the check"* — in files that contain no tests. The M10 framing lead-in re-attributes the prose ("The contract **they** pin"), and these sentences contradict it six lines later | Round-2 prose lens, findings 5 and 8 | **Fixed** — 12 rewrites across 9 files; the swept population is every `_*_fixtures.py` docstring, 22 self-referential hits, of which the 10 with the file as subject were false and the rest are correctly re-attributed by the lead-in |
| M21 | Seven glob references match the **referencing file itself** — `test_analyze_logs_behavior.py:4` says *"the sibling ``test_analyze_logs_*.py`` … drives ``cmd_run`` only through ``run_script``"*, and the glob now includes this file, which drives it in-process. The M2 sweep created these by repointing a bare name onto a successor glob | Round-2 prose lens, finding 7 | **Fixed** — six repoint onto the bare name M16 restored; the seventh names its two actual siblings, which is more precise than the glob it replaces |
| M22 | 25 glob references of the form `X_*.py` cannot match `X.py`, so once M16 restored 47 bare modules each such glob **under-covered** the family it names | Round-2 follow-through; `classify_losses.py` reported 22 unexplained absences, all of this shape | **Fixed** — widened to `X*.py`, which covers both. `UNEXPLAINED` back to 0 |
| M23 | The report's D2 surface check — *"every other slice's count is unchanged … a stray edit outside the surface would have moved one of them"* — cannot detect what it claims. The rule is a 400-line threshold, so a sub-threshold edit moves no count. It missed **16** in-budget modules this run edited | Round-2 contract lens, findings 2–3 | **Fixed** — replaced by the changed-set check D2 actually asks for (§ D2), which reports 0 files outside the surface and names the 16 as a stated departure |

### Rounds 3 and 4 — move-induced, all fixed

| # | Finding | Evidence | Disposition |
|---|---|---|---|
| M24 | **19 modules claim a negative test they do not have.** `_seed_guarded_plan_dirs`'s docstring says the guard keeps positive tests seeded *"while the negative tests (which call ``_register_unseeded``) still exercise the real ``plan_not_found`` failure"*. Pre-split that was true in all 3 modules carrying it; the split duplicated the fixture into 21, of which **2** call `_register_unseeded`. In the other 19 the sentence describes tests that are not there, and the `if plan_id not in _UNSEEDED_PLAN_IDS` guard it describes is constant-true | Round-3 fixtures lens, finding 3; verified by separating *calls* from *mentions* across the directory | **Fixed** — the 19 now say what their module actually does. No assertion was lost: all three pre-split negative tests survive in the two registering modules |
| M25 | ⛔ **167 constructs across 50 files sat under a different `# ====` section banner than the source gave them.** Ten `log_lock_event` tests filed under *"rmw_json — serialization under concurrency (TOCTOU correctness)"*; nine width-agnostic numbering tests under *"Tier 2: scan subcommand"*; 30 banners had travelled into a `_*_fixtures.py` holding no tests, where they titled a helper. A banner is a claim about what follows it, and no suite, multiset diff or linter encodes that claim | Round-3 partition lens, findings 1–6; nearest-preceding-banner attribution diff, source vs HEAD | **Fixed to 28** — 97 banners inserted at the head of the run each introduces. The 28 that remain are in **`manage-findings/test_findings_store_resolve.py`, `manage-status/test_manage_status_transition_loop_back.py` and `manage-status/test_title_token.py`** — the three the budget guard protected (M26). ⚠️ An earlier draft said they were "named under M26" when M26 named none of them: disclosure a reader cannot act on |
| M26 | ⛔ **M25's first fix was a regression on the deliverable, and this report shipped it unmeasured.** Inserting a banner above *every* construct whose section header had been left behind added ~900 lines across 110 files: it pushed **seven** modules back over the 400-line budget (slice 4 → 11, whole tree 259 → 266) and created **four** new `test-docstring-historical-prose` findings (200 → 204). The report's figures were taken at the commit before it | Round-4 report lens, findings 1–3; doctor sweep at every commit on the branch | **Fixed** — two rules make the repair free. Insert only where a construct sits under a **non-empty wrong** banner (an absent banner claims nothing, so it cannot be false), and **never spend a module's budget compliance on a comment**. Insertions fall 228 → 97; slice back to **4**, whole tree **259**, historical-prose **200**, `total_issues` **578** — every rule at the value it had before the repair |
| M27 | The banner repair's first implementation preserved every construct and still dropped **154 distinct code lines**: the block walk ended the final block at the last construct rather than at end-of-file. Its second dropped the three-line note explaining why `_tasks_crud` is loaded through `importlib` exactly as it is — the banner headed a module-level load, which is not a `def` or a `class`, so "introduces nothing" deleted it | The multiset diff, both times; neither was visible to ruff, mypy or the suite | **Fixed** — deletion is now restricted to a genuinely empty section (0 banners deleted), and the repair asserts per file that the multiset of non-blank non-banner lines is unchanged before it writes |
| M28 | The loss classifier was fed the **whole** `origin/main...HEAD` diff as its declared-corrections set — 22,451 lines — which let it explain any absence by construction. `UNEXPLAINED: 0` was true and meaningless | Noticed while re-running it after round 3 | **Fixed** — the declared set is now the diff of the correction passes alone (82 lines). Rebuilding it is what surfaced M27's lost rationale, which the vacuous version had absorbed |

### Round 5 — the round that asked whether the result is any good

The first four rounds compared the tree to itself or to its own past: same tests, same coverage sets,
same texts, same figures. **None of them asked whether the output is a codebase anyone would want to
work in.** Round 5 did, and its verdict on the PR as it then stood was *"no — not as it stands, though
I would merge a near neighbour of it."*

| # | Finding | Evidence | Disposition |
|---|---|---|---|
| M29 | ⛔ **M1's fix claim is false, and the metric that certified the split is the same fact as the defect.** M1 says the fix made "each output's docstring **true of that output**". It did not: it truncated the inherited docstring to its summary *paragraph*, and that paragraph is often the sentence enumerating the whole original contract. **Three summary lines enumerate several subjects and are shared by 12 modules that each hold one of them** — `test_manage_status_transition_archive.py` and its five siblings all opened "Tests for manage-status.py transition + archive + delete + orphans + loop-back". ⭐ The insight no earlier round could reach: *"0 unexplained comment diffs" and this defect are the same fact.* A split that creates 199 modules and rewrites no module docstring cannot have produced 199 self-describing modules — the invariance metric rewarded exactly the behaviour that hollowed out the prose | Round-5 lens, finding 1 | **Fixed for the 12** — each now carries a summary line naming what that module holds, written from its own clusters and re-parsed to confirm. **Not fixed, and stated instead:** 53 further summary lines are shared by 177 modules. Those are *unspecific* rather than false — "Tests for manage-metrics.py CLI script." is true of all 15 that carry it — so nothing false is left, but M1's "true of that output" is corrected to **"true of that output, and in 177 cases no more specific than of its siblings"** |
| M30 | A one-test module carries three autouse fixtures, of which `_stub_resolver_seam` is **dead** — the single test re-patches the same seam itself at `:87` — while the other two describe "the bulk of this file" and "cases that exercise the short-circuit", in a file with one case and no such cases | Round-5 lens, finding 5 | **Fixed** — the dead fixture and its now-unused import are gone; the two docstrings describe one case |
| M31 | The report cross-referenced "the three files named under M26" and M26 named none of them: 28 mis-attributed banners, disclosed in a form no reader could act on. Two more of the same shape: a false clause corrected in § D2 and restated verbatim five paragraphs later, and a helper-module line count stale in the table while the prose four lines below carried the right one | Round-5 lens, findings 2–4 | **Fixed** — the three files are named, the clause is corrected where it recurred, and the table reads 730 |

⛔ **M32 — two disclosures that are true sentence by sentence and misleading as a whole.** Round 5's
sharpest structural finding, and neither is fixed by a figure:

1. **The report declined a known-correct fix to protect its own figures.** § D2 establishes that D2's
   hoist clause licenses moving helpers "that more than one resulting module needs", finds **nine**
   sources that produced exactly one module plus a fixtures module, says a follow-up splitting them
   "would bring both the method and the hoist inside the letter" — and then declines, because
   *"re-running the emitter over them would re-open every measurement in this report for no change the
   rule can see."* Read plainly: **the report became the optimisation target.** The disclosure is what
   makes it read as candour. It is restated here as what it is, and the nine are residue for a
   follow-up rather than a bounded acceptance.
2. **`count: 0` on this rule will certify file naming, not module size.** The slice's helper modules go
   6 files / 1,572 lines → 70 / 12,217, and the rule cannot see any of it. § D2 answers *"is this a rule
   evasion?"* — no, a file with no tests is not a test module — and that is not the live question. The
   live question is what the rule certifies once the campaign flips it to `error`: on this run's
   precedent, roughly 10.6k lines per slice migrate out of measurement, on the order of 50k across seven
   slices. **This report prices its own slice and no round could see the campaign**, because every
   round's population was slice `050`. It belongs to whoever owns the flip (plan `090` § D7's ladder),
   and it is raised here rather than left to be discovered at zero.

### Round 6 — auditing the fixes, and reading the helpers as a maintainer

**Every fix is unverified except by the round that follows it, and the last round's fixes are verified
by nobody.** Round 6 audited all 32 dispositions against the tree and read the 64 helpers as files
someone has to live in. It returned **five overstated or false dispositions, two fixes that introduced
new defects, and a section this run re-staled after M31 closed that exact class.**

| # | Finding | Evidence | Disposition |
|---|---|---|---|
| M33 | ⛔ **M27's guarantee is self-refuting, and the repair it guards shipped duplicate banners.** Its promise is that the repair "asserts per file that the multiset of non-blank **non-banner** lines is unchanged" — an assertion that by construction **cannot see a banner the repair added**. It added three: an inserted block sitting immediately above a near-identical one already in the file, differing by one word because M2's directional pass had edited the resident copy. One landed in a **399-line** module, a line from re-entering the budget | Round-6 fix audit, item 3 | **Fixed** — a dedup pass removes a banner block separated from another by nothing but blank lines, keeping the copy the file already carried (which holds later prose corrections). Three removed, then a fourth after the `# ---` sweep below |
| M34 | ⛔ **M25's banner repair swept only `# ====` rules.** The `# ----` population was never looked at, and every one of the three files M25 named uses `====` exclusively — so the "28 remaining, in three files" was exact for a population chosen by the tool rather than by the defect | Round-6 fix audit, item 2; three survivors named in `test_extract_chat_signal_cmd_run.py`, `test_manage_change_ledger.py`, `test_manage_change_ledger_append.py` | **Fixed** — the rule now matches both styles. Re-measured over both: **33 → 28**, and the 28 are again the three files the budget guard protects, now for a reason about the defect rather than about the tool |
| M35 | ⛔ **M29's "three enumerating summary lines" was keyed on the first physical LINE, and M1's fix preserves the summary PARAGRAPH — which wraps.** Any conjunctive summary spilling onto line 2 was invisible to it | Round-6 fix audit, item 1 | **Fixed** — re-derived over the paragraph: **7 shared paragraphs name several subjects, over 19 modules**, of which **5 are false of a carrier** and are rewritten. Two are not: "the storage engine for findings and Q-Gate findings" and "the persisted denominators and their sampling-point discriminator" describe one subject with two aspects, and are true of every carrier |
| M36 | Two pronoun inversions **this run's own M20 rewrite introduced**: swapping "This module complements it" to "Those tests complement it" moved the antecedent onto the sibling, so the paragraph asserts that file complements itself. Found in two different bundles, which makes it systematic to the rewrite rather than a slip. A third swap changed one verb of a compound predicate and not the other ("They drive it … and asserts on") | Round-6 maintainer lens, findings 4–5 | **Fixed** — the subject is now "The modules this preamble serves"; five sentences corrected across three files |
| M37 | **The lead-in M10 added over-promises.** It reads "Holds the module-level loads, constants and helpers those modules **share**. The contract they pin, **in full**:" — over prose that in **51 of 55** helpers opens by declaring the file to be tests, in files holding none; that in several cases is three words under a completeness claim; and where **12 helpers share nothing at all** (every exported name used by exactly one consumer) | Round-6 maintainer lens, findings 1 and 7 | **Fixed** — the lead-in now says what the text *is* rather than what it guarantees: "Holds the module-level loads, constants and helpers the modules beside it import. Below, verbatim, is the docstring of the module they were split from." Rewritten in all **55** |
| M38 | Five surviving locatives — three "here"s in a file that pins nothing and a "below" pointing into two sibling modules — plus 56 blank lines of mechanical over-padding, one helper spending 35 lines on 8 imports | Round-6 maintainer lens, findings 6, 12, 13 | **Fixed** — locatives rewritten; blank runs collapsed to PEP 8's two across 15 files |

⛔ **M39 — the split tripled the duplication the helper layer exists to absorb. Fixed on operator
instruction, after this report had recorded it as out of scope.**

Round 6's hardest number: `_seed_guarded_plan_dirs` went from **8 files pre-split to 28**, and
`manage-locks/_manage_locks_merge_lock_fixtures.py` *defined* `isolated_base` and `_stub_title_tokens`
while **nine of its ten consumers carried byte-identical local copies**. Across the ten directories:
**12 fixture names duplicated over 1,183 redundant lines**, roughly a quarter of the slice's growth.
The helper layer had captured the constants and the module loads — the cheap part — and left the pytest
fixture surface, which is the part that costs a reader.

**This report first declined to fix it**, on the ground that § Out of scope excludes "hoisting fixtures"
in as many words. The operator's instruction overrode that reading. The result:

| | before | after |
|---|---:|---:|
| Fixture names carrying a duplicated dominant body | 12 | **4** |
| Redundant lines | 1,183 | **100** |
| Local copies replaced by an import | — | **49** |
| Slice line growth over `origin/main` | +6,548 (+7.2%) | **+5,213 (+5.7%)** |

**Three rules kept it a move rather than a rewrite.** Only the **dominant body** of each name moves —
several of these names carry more than one, and `_seed_guarded_plan_dirs`'s second body seeds
unconditionally where the first honours a registry, so hoisting across that difference would change
behaviour; every non-dominant copy stays exactly where it is. The home must be a helper the carrier
**already imports**, so no module gains a dependency edge. And the fixture only moves when every free
name it reads is already bound at that home — which is why `_seed_guarded_plan_dirs` landed in **six**
different helpers rather than one, each already binding the `_UNSEEDED_PLAN_IDS` and `manage_metrics`
its body reads.

**The four that remain are blocked, and by what is stated rather than left as a count**: `_stubbed_invariants`
(29 lines, needs `_cmds`/`_inv`), `_stub_resolver_seam` (28, needs `file_ops`/`worktree_query_result`),
`env` (27, needs `Env`/`_init_repo`/`_run`) and `_stub_metadata` (16, needs `_cmds`). Each reads a name
bound in the carrier and in no helper, so moving the fixture means moving that too — a larger change
than a hoist.

⭐ **A second instruction widened this from fixtures to all duplicated code, and the rules that
survived it are the interesting part.** The split had also duplicated plain helper functions, constants
and module-load bindings — `cmd_create = _lifecycle.cmd_create` in ten modules, `_write_status` in
three, `SCRIPT_PATH` in three directories at once: **32 names over 257 further redundant lines.**
Generalising the hoist to every top-level definition took **three attempts, each stopped by a different
real constraint**, and each constraint is now a rule the pass enforces:

1. **A cross-unit import is worse than the duplication it removes.** The first attempt picked the
   shortest-named helper that happened to bind the free names, and had
   `test_analyze_logs_behavior.py` importing from `_compile_report_fixtures`. The home must belong to
   the carrier's own unit, or be the directory's canonical helper — nothing else.
2. **A module-load binding must not move**, because it registers a name in `sys.modules` and D3 exists
   precisely about that. Hoisting one produced `loader for manage_metrics_helpers cannot handle
   manage_metrics` immediately. The exclusion covers the whole `importlib` dance, not only the
   registering call: `manage_metrics = importlib.util.module_from_spec(_spec)` names no loader but is
   one half of a pair, and moving it away from its `exec_module` left the object bound to another
   file's spec.
3. **Nor may anything DERIVED from one move** — one level removed and far quieter.
   `cmd_create = _lifecycle.cmd_create` reads a module object that is distinct per file, so hoisting it
   made a test patch one object and call another. Seven tests failed with an empty log spy, and nothing
   about the change looked wrong.

**Result: 27 names / 215 redundant lines remain, of which 74 lines are locked by module identity** —
the rules above, not a shortfall of effort. Slice growth ends at **+5,184 lines (+5.7%)** against
`origin/main`, from +7.2% before any of this.

⚠️ **The cost is real and is a widened lint blind spot, not a line count.** A fixture reached by import
is unused *as a name*, so `ruff --fix` deletes the import and the fixture silently stops existing —
which is exactly what happened on the first attempt: **22 "fixture not found" errors** from imports the
autofix had removed. Every hoisted import therefore carries `# noqa: F401`. And where a test takes the
fixture as a **parameter**, `F811` fires at the parameter, so only a module-level directive reaches it:
**19 modules** now carry `# ruff: noqa: F811`, up from the 1 this report previously reported. Those 19
lose redefinition checking — the guard against two `def test_x` in one namespace, where Python keeps the
last and the first silently stops existing.

**That risk is bounded rather than asserted away:** all 19 were checked for a duplicate definition in
every namespace, module level and class body alike, and the count today is **0**. The blind spot is
real, currently empty, and named here so a follow-up can close it with a tree-wide guard rather than
per-module lint.

⭐ **And the empirical answer to the question this report flagged as open.** § D2 said hoisting "costs
two suppressions" and round 6 recorded that whether a *strictly autouse* fixture costs `F811` was not
established. Measured: **`_stub_title_tokens` is autouse and still costs it**, because two modules take
it as a parameter to inspect the recorder. The cost is **per module, on whether any test in it names the
fixture as a parameter** — not a property of the fixture's kind. 19 of the 49 hoisted call sites pay it;
30 do not.

⚠️ **One correction a follow-up needs, and one uncertainty it must not inherit as fact.** § D2 states
that hoisting a fixture "costs two suppressions: `F401` on the import … and a module-level
`# ruff: noqa: F811`". That is **established for the one module that hoists** — round 2 measured 23
F811 diagnostics under its directive, 15 for `isolated_base` and 8 for `_stub_title_tokens`. Whether a
fixture that is *strictly* autouse and never named as a parameter would cost F811 at all is **not
established**: an isolated probe suggested it would not, and the in-repo evidence points the other way,
so the honest statement is that a follow-up must measure it rather than assume either answer. Writing
the convenient one down without checking is the M12 shape, and this report has done that once already.

⭐ **M26 is the sharpest thing this run has to report about itself.** § "What have we learned" proposal 2
— *"A long measurement is invalidated by any edit to its subject. Take it last, after the tree is final,
and re-take it if anything changes"* — was written by this run, in this report, and then violated by
this run in the very next commit. The rule was known, stated, and not applied. What caught it was not
the rule but a reader asked to re-derive every figure against the tree; nothing else would have, because
every other signal was green.


Every one of M7–M9 was found by re-measuring **all seven** rules whole-tree rather than only the one
this plan targets. The final sweep has `test-module-line-budget` at **259** and the other six at
exactly their **main-side** values. ⚠️ Two earlier drafts said "256 … and the other six at exactly
their pre-split values". 256 was the count at `c05b998`, four commits before the shipped tree and
before the merge of main; and the six sit at their main-side values, not their pre-split ones —
`test-module-preamble-boilerplate` is 104 on main against a pre-split 100. Both halves were stale.

⚠️ **18 of the 142 labelled modules still carry a label true of under half their tests, and that is a
shipped defect, not a clean result.** The metric is mechanical: for the most generous split of the
filename into unit and label, what share of the module's tests sit in a cluster whose own name contains
the label as a contiguous run of words? `test_manage_adr_next_number.py` scores 7% — 15 one-test
clusters, the label true of one. The 57 modules that kept their source's name are excluded from the
metric, and ⚠️ **the stated reason for excluding them is only true of some of them.** The reason given
was: *"a filename that names only the unit makes no cluster claim, so there is nothing in it that can be
false."* That holds for a bare unit name. But at least six of the 57 are a unit name **plus a label**
whose bare form now exists as a sibling — `test_manage_metrics_phase_boundary.py` beside
`test_manage_metrics.py`, `test_planning_lane_corroboration.py` and `test_planning_lane_request_body.py`
beside `test_planning_lane.py`, `test_check_artifact_consistency_behavior.py` and
`test_compile_report_behavior.py` beside their bare forms. Each of those is now a residue bin, and its
inherited label is exactly the thing that can have become false. **So 18 of 142 is a lower bound, not a
measurement of the whole population**, and the excluded 57 have not been checked. The 18 that remain are bins that do carry a label
and where the label does not carry.

⚠️ **The fix has a cost and it is stated in full: sibling name pairs where one is a strict prefix of
another go 19 → 141.** Every restored unit name prefixes every labelled sibling from the same source.
That metric exists to catch the standard's "the next author cannot tell which half a new test belongs
in" harm — and here it does not carry that harm, because the question has an answer: if the new test
fits a sibling's label it goes there, and otherwise it goes in the unit module. **That is an argument,
not a measurement, and it is offered as one.** A reader who thinks 141 prefix pairs is the worse trade
against 47 false names has the numbers to make that case.

⚠️ **M1, M9 and M10 are the same defect found three times, each time in the place the previous fix put
it** — and M13 is a fourth, the M2 sweep missing five instances of the class M2 exists to remove. M1 was the docstring replicated into every output; M9 was the fixtures module copying a docstring
the single output already had; M10 was the inherited docstring heading a file it did not describe. Each
fix was sound where it landed and moved the claim somewhere the next round had to find it.

⭐ **The single most useful thing this run did was disbelieve its own rationale.** M12 was a sentence
this run wrote to explain a decision, never checked against the tree, and then relied on as the reason
a module could not meet the budget — and the counter-example was one grep away, in a file this
repository already ships. Nothing in the build gate could have caught it: the suite was green, the
linter clean, and the sentence type-checks as prose. **The deliverables should be read as still
carrying defects of that kind**, since the only instrument that found this one was an independent
reader asked to verify the claims rather than the code.

### The two cold reads

§ Verification requires a cold read: three split modules and their `_{domain}_fixtures.py`, given to a
sub-agent with **no other context**, asked of ten named tests "what contract does this test pin, and
why does it matter?" It was run twice — once on the split as first written, and again after the fixes
above, which is what the plan means by "re-read".

| | First read | Second read |
|---|---|---|
| RECOVERABLE | 6 of 10 | **7 of 10** |
| UNRECOVERABLE | `test_a_re_entered_phase_is_its_own_shape`, `test_default_max_slots_is_five`, `test_missing_fragments_file_errors`, `test_session_id_default_string_when_missing` | `test_default_max_slots_is_five`, `test_missing_fragments_file_errors`, `test_session_id_default_string_when_missing` |

The answers are recorded in full in the run's own working notes; the verdicts and the reasons are
reproduced here because they are what the deliverable turns on.

**The one that moved** — `test_a_re_entered_phase_is_its_own_shape` — became recoverable because the
second reader could reach the fixtures module's docstring, which states the mechanism ("the aggregate
is cumulative, the ledgers are not") that the first reader could not resolve. Nothing about that test
changed.

⚠️ **The second read also states a cost this run should not hide.** Asked directly whether splitting
the docstring hurt, it answered yes for two of the three pairs: *"the mechanics stayed with the tests,
the reasoning left."* The full contract prose is one file away from the tests it explains. That is a
real loss of locality, accepted deliberately: the alternative is M1, where every output module states a
contract it does not hold, and **recoverability measured over the file set the plan itself specifies
went up, not down** (6 → 7). The trade is disclosed rather than presented as a clean win.

For the third pair the reader reported the premise did not even hold: `_compile_report_fixtures.py` and
its test module carry the same one-line description of the subject, so there the problem is not
misplaced rationale but absent rationale, which is a pre-existing gap. ⚠️ An earlier draft said the two
docstrings were "byte-identical … the same seven-word line". They are not:
`_compile_report_fixtures.py:2-7` opens with M10's framing lead-in, and `test_compile_report.py:2` is
three words. The conclusion holds; that evidence for it did not.

### Pre-existing, recorded not fixed

The **first** cold read (§ Verification, "By reading") found 6 of 10 tests recoverable; the second, taken
against the tree as shipped and reproduced in the appendix, found **7 of 10** with `E`, `H` and `I`
unrecoverable. The table below is the first read's four, kept because its extra row —
`test_a_re_entered_phase_is_its_own_shape`, which the second read recovered — carries the same
pre-existing verdict and is worth the record. Each is established mechanically rather than asserted: each test's
source was extracted at the pre-split commit and from the tree now and compared byte for byte.

| Test | Body byte-identical across the move | Carried a docstring before the move |
|---|---|---|
| `TestTheTwoPartialityShapes::test_a_re_entered_phase_is_its_own_shape` | yes | yes — preserved verbatim |
| `TestAdmission::test_default_max_slots_is_five` | yes | **no** |
| `TestFaultPaths::test_missing_fragments_file_errors` | yes | **no** |
| `TestSessionIdPassthrough::test_session_id_default_string_when_missing` | yes | **no** |

The plan's remedy for an unrecoverable answer is to *restore* the rationale lost in the move. **No
rationale was lost**: three of the four never carried one, and the fourth's is intact. Writing new
rationale here would be authoring claims about production code this run did not read — the
invented-rationale defect rather than a fix — and § Out of scope assigns prose work to the slice's own
reduction plan. So they are **recorded**, and the owner is plan `050`'s residue.

The cold read raised further pre-existing items, none of which this plan may fix (§ Out of scope
excludes `marketplace/bundles/**`, `test/conftest.py`, and prose work). Recorded with their owners:

| Finding | Owner |
|---|---|
| `test_build_queue_admission.py`'s docstring pins a `build_queue.max_slots` config path while its fixture writes `build.queue.max_slots` — the documented contract names a path the suite never exercises | `050` residue (prose) — or a real production defect, in which case `090` |
| `_ledger_reconciliation_fixtures.py::_boundary_timestamps` hand-parses boundary TOON by `str.split(',')` and skips a literal `'rows[]'` prefix, while the writer emits the tabular `rows[N]{cols}:` form — the header row would not be skipped | `090` if the writer's form is as described; otherwise `050` residue |
| `EXEMPT_RULE_IDS`-style bare literals asserted as contracts with no shared named constant (`'cumulative across closes'`, `'end_time'`, `'failed to delete fragments bundle'`, the `100`/`150` run-log bound, the `5` default slots) | `050` residue |
| Two constants with byte-identical values in `_compile_report_fixtures.py` (`_COLLECT_FRAGMENTS_SCRIPT`, `_COLLECT_FRAGMENTS_SCRIPT_REGISTRY`); a dead `content` assignment in `_write_fragments_with_dispatch_boundaries`; an unused `plan_dir` local | `050` residue |
| An autouse fixture (`_seed_guarded_plan_dirs`) that monkeypatches production `require_plan_exists` to *create* the directory it guards. ⚠️ An earlier draft called it "undocumented … with no docstring saying why"; it carries a seven-line docstring on both sides of the move. The finding is the patching, not an absence of prose | `050` residue |
| Stale external pointers with no in-repo target (`solution_outline.md D5`, `lock-reconciliation-analysis.md §5`, `ADR-002`, `Task-4 coverage`, two bare commit hashes) | `050` residue (prose) |
| `test_session_id_default_string_when_missing` discards `run_script`'s return and never asserts `result.success`, unlike its sibling one test above it — a script failing before the write would surface as a confusing file mismatch rather than the real error | `050` residue |
| `test_missing_fragments_file_errors` asserts only `not result.success` — no exit code, no message, and no assertion that no report was written, which is the half that matters if a missing bundle could yield a hollow-but-plausible report | `050` residue |

**Filename-versus-content drift was this run's, and an earlier draft of this report argued its way out
of fixing it.** The cold read noted that `test_ledger_reconciliation_manifest_parsing.py` held one
manifest-parsing test out of ten, and that `test_compile_report_fault_paths.py` ended with a
registry-consistency guard that is not a fault path. This report called that "the naming rule's limit
rather than a bug in it" and declined the remedy — regrouping clusters by theme — as "a larger change
than this deliverable licenses".

⭐ **That argument was wrong, and it is worth naming why, because it is the M12 shape again.** The
premise was true (adjacency packing cannot produce a true name where adjacent clusters share nothing)
and the conclusion did not follow: the plan's own standard is that a module is "named for the behaviour
it pins", so a name true of one cluster in ten is not a limit to disclose, it is the deliverable
failing. And the licence question was never asked of the plan — a split that reorders tests between
files is exactly what "split by behaviour cluster" means. The regrouping is now done and recorded as
**M14**; it cost one further rebuild, and it moved the whole-tree budget count not at all.

## Verification conditions

| Condition | Before | After | Verdict |
|---|---|---|---|
| 1. Collected test count does not decrease (slice) | 4207 | 4207 | **holds** — identical, not merely non-decreasing |
| — `test-module-line-budget`, slice | 66 | **4** | 62 modules brought inside the budget |
| 2. Coverage does not decrease (slice bundle paths) | 89% | 89% | **holds** — bit-identical: 9986 statements, 962 missed, 3682 branches, 355 partial, both sides |
| 3. Order-independent (default **and** reverse directory order) | — | 4207 passed both | **holds** |
| 4. `EXEMPT_RULE_IDS` unchanged | n/a | n/a | **not applicable** — that check is stated for the `080` slice; this run is `050` and touches no plugin-doctor module |
| 5. Suite not slower, skipped count not higher (whole tree) | 21070 passed, 14 skipped, 1958.89 s | _pending_ | _pending_ |

## Reviewer participation

**Population derived from configuration**, not transcribed: the `author_login` of each registry doc
under `marketplace/bundles/plan-marshall/skills/automatic-review/standards/` — `coderabbit.md`,
`pr-agent.md`, `sourcery.md`.

| Reviewer (`author_login`) | Surface it posted on | Verdict | Reopens? | Body evidence |
|---|---|---|---|---|
| `cuioss-review-bot[bot]` | **issue comment**, not a review | `reviewed` | — | *"PR contains tests · No security concerns identified · No major issues detected"* |
| `coderabbitai[bot]` | issue comment | `rate-limited` | **no** (`no-reopen`) | *"Review skipped — Too many files! This PR contains **281** files, which is 181 over the limit of 100…"* — plus a second, remediable reason: *"This review couldn't start because sufficient usage credits or metered capacity aren't available… then retry."* |
| `sourcery-ai[bot]` | review, state `COMMENTED` | `unobtainable` at the time; **the ceiling no longer binds** | see below | *"Sorry, we are unable to review this pull request. The GitHub API does not allow us to fetch diffs exceeding 300 files, and this pull request has 317"* — submitted against `325f58c` |

⚠️ **The surface column exists because an earlier draft of this report said `cuioss-review-bot`
"published a review against the diff", and it did not.** Its verdict is an issue comment
(`#issuecomment-5349874474`); the only entry on the `get_reviews` surface is Sourcery's refusal. That
distinction matters to anyone reading the participation table as evidence of review depth: a bot that
comments on a PR has not necessarily read its diff, and this one posted a three-line summary against a
318-file change. The verdict `reviewed` is kept because the bot's own posture is a review verdict, but
the surface is now stated so the reader can weigh it.

The two file-count figures differ because the reviewers counted at different moments: Sourcery refused
at 317 files against the head of that time, CodeRabbit's comment was last updated against `c05b998` at
318. Both are quoted as posted.

**Coverage: 1 of 3.** The § Step 8 condition 5 disclosure fired and said exactly that.

⛔ **Two of this section's load-bearing claims went stale under the run's own pushes, and a reader
should have the current state rather than the one that was true when it was written.**

**CodeRabbit's notice is live and re-renders on every push.** It now reads 281 files, not the 318 an
earlier draft quoted — and it carries a *second* reason the earlier draft did not mention: a usage-credit
condition that explicitly names a retry. That second reason is remediable and a retry could clear it. The
`no-reopen` arm still holds, but on the size ceiling alone: 281 files against a limit of 100 is a refusal
no wait or retry can change, independently of credits.

**Sourcery's ceiling no longer binds this PR.** Its limit is 300 files; it refused against `325f58c`,
which was 317. The shipped head is **281 files — inside the ceiling.** The run has pushed six times
since, which is the route the lane says an auto-review reviewer honours, and Sourcery's check run on the
current head reports `skipped` rather than a fresh refusal or a review. So its verdict is **not**
`unobtainable` on the ceiling any more; it is a reviewer that had the opportunity and did not take it.
The honest arm is `could-not-re-enter`, and the honest statement is that this run does not know why.

⚠️ **This also weakens the structural claim below.** *"Runs 2 through 7 will each be refused by the same
two reviewers for the same reason"* is not established, because this run's own final head fell back
under one of the two ceilings as the diff consolidated. It remains true of CodeRabbit's 100-file limit,
which no slice-sized PR will meet.

⚠️ **Neither refusal is a clock, and that is the whole point.** Both are ceilings on *this diff's size* —
100 files for one reviewer, 300 for the other — so `Reopens? no`: no wait, no retry and no jitter
schedule can change them, and the lane's retry budget does not apply. Condition 6 is satisfied on its
`Reopens? no` arm rather than by spending attempts against a mechanism that cannot deliver.

⛔ **This is a structural finding about the campaign, not an incident on one PR.** A slice split
produces a PR of roughly this size by construction — 66 sources became 263 modules here — so **runs 2
through 7 will each be refused by the same two reviewers for the same reason**. Two thirds of this
repository's automated review capacity is unreachable for the campaign as the plan currently shapes a
run, and no run can fix that from inside itself: the remedy is a plan-level decision about how a slice
is carved into pull requests. It is recorded in § Residue and raised to the operator rather than
absorbed.

The inline review-thread surface (`get_review_comments`) returned an empty set and the read succeeded,
so that is a genuine absence rather than an unreadable surface. All three surfaces were read.

**Operator disposition.** The shortfall was put to the operator, who instructed that the reviewers
which structurally cannot review this diff be ignored, and authorised the landing. § Step 8 condition 6
is therefore satisfied on its `Reopens? no` arm *and* by explicit operator instruction; the run records
the instruction rather than treating the gate as met on its own reading. The operator also directed a
final adversarial verification of five rounds before landing — recorded in § Findings.

Every comment on the PR was dispositioned: two are refusal notices needing no action, one is a clean
review with no findings. No comment was left open.

## Cost

- **Tokens:** not available to the agent in this session — the harness does not expose a token count to
  the run, so no figure is stated rather than one being estimated.
- **Wall-clock:** the run's first commit is stamped `2026-08-19T22:32:22Z`. The session spanned a
  container restart, so elapsed wall-clock over-counts the work by the length of that outage; the
  figure is not stated as a work duration for that reason. What *is* measurable and comparable is the
  instrumented part: the whole-tree suite took 1958.89 s before the change (see § Verification
  conditions for after), the slice takes about 185 s per run and was run six times, and the whole-tree
  `test-conventions` sweep about 40 s and was run seven times.
- **Population:** these figures count **this single cloud session's own subprocesses**, measured from
  their own start/end stamps. ⛔ They are **not comparable** to a plan-marshall `metrics.toon` total,
  which counts an orchestrator-plus-agent dispatch tree under a per-task billing boundary this lane
  does not share. No attempt is made to reconcile them.

The dominant cost of this run was not the split. It was **re-running the whole verification chain after
each correction** — the tree was rebuilt from the pre-split sources and re-verified end to end seven
times, because each round of findings changed the emitter rather than the output. A run 2 that inherits
the rules in § D2 and § D4 pays that once.

## Contract check (Step 9)

**GitHub access path:** the GitHub MCP server. There is no `gh` CLI in this session.
**Branch form:** harness-assigned (`claude/module-budget-campaign-test-3gbpv6`), kept as-is per the
lane's resume rule. This run did not create a branch, so the closed prefix set does not apply to it.
**Arrival:** first run, then **resumed after a container restart** — the VM was reclaimed mid-run and
its replacement re-cloned. Nothing was lost, because every commit had been pushed: the working tree
came back clean with `HEAD` identical to `origin`. That is the durability rule paying for itself.
**Plugin cache sync:** not owed. It is a machine-local build step a cloud run never performs.

| Step | Verdict |
|---|---|
| 1 Skills loaded | **done** — named in § Skills loaded, all read by bundle path |
| 2 Branch | **done** — on `origin` before the first edit; survived a container restart intact |
| 3 Plan directory | **done** — `doc/plans/test-quality/100-module-budget-campaign/plan.md`, opening with the first-instruction block, which was present and needed no repair |
| 4 Implement | **done** — commits carry the trailer, no "Generated with" footer |
| 4 Per-commit gate | **done** — every commit touching `*.py` was preceded by `./pw quality-gate` reporting `issues[0]` with ruff, mypy and the SPDX check each clean |
| 4 Pushed | **done** — no unpushed commit at any point; proven by the restart |
| 5 Build gate | **done** — Python changed, so the full gate applies. CI ran `verify / verify` to **success** on this exact head SHA, which is the authoritative result; a local `./pw verify` was run as well |
| 6 Verification sub-agent | **done** — see § Findings and the stop record below |
| 7 PR cycle | **done** — PR #1314; all three comment surfaces read; every comment dispositioned; participation table carries a verdict and a `Reopens?` value per reviewer |
| 8 Merge gate | see below |
| 8 Bridge | **done** — nothing written under `doc/plans/` outside this plan's own directory; no ledger, no status file, no other plan touched |
| 9 This check | **done** — this table |
| 9 What have we learned | **done** — below |

**Step 5 note, stated rather than glossed:** the local `./pw verify` and the whole-tree suite were each
started, killed and restarted more than once, because a code change landed after they began. A run that
measures a tree it then modifies has measured nothing; the figures reported here come from runs against
the final tree, and the discarded ones are named as discarded.

## What have we learned (Step 9)

Three proposals, each resting on something that happened in this run rather than on a preference.
**None is self-approved**; per the lane they are put to the operator and, if accepted, ship as a
separate `chore/` PR touching only the skill.

### 1. A refactor that MOVES text proves fidelity by a multiset diff, not by a green suite

**Evidence.** Seven tests vanished from this branch and every signal stayed green: the suite passed,
the target rule's count fell, ruff and mypy were clean, and the doctor sweep reported progress. Two
output bins had resolved to the same filename and the second write replaced the first. The only
instrument that saw it was a multiset diff of `Class::test` against the pre-split sources. The same
instrument, applied to comments, is what confirms the epic's own recorded disaster — plan `050` losing
162 column-0 comments — did not recur.

**Why the contract needs it.** § Step 6 tells a run to sweep for stale claims and to mutation-test a
new guard. It says nothing about the class of change where the *content is supposed to be identical*
and only its location moves — a split, an extraction, a rename, a file merge. For that class a green
suite is not evidence, because a test that no longer exists cannot fail.

**Proposed edit**, into § Step 6 as its own paragraph: *"When the change is a MOVE — a split, an
extraction, a merge, a rename — the deliverable's fidelity is measured as a multiset diff against the
pre-change sources, not asserted from a green suite. Compare comments, non-blank non-comment lines, and
test identities as counted multisets, so a text that vanished cannot be masked by one that was
duplicated. A green suite cannot see a test that no longer exists."*

### 2. A long measurement is invalidated by any edit to its subject

**Evidence.** This run started the whole-tree suite three times and discarded two of them: the first
because a later finding changed the emitter, the second because prose fixes landed mid-run and a
second pytest session ran concurrently, which corrupts a wall-clock comparison. Roughly an hour of
compute was spent on measurements that could not be reported.

**Proposed edit**, into § Step 5: *"A measurement that takes longer than the work is invalidated by any
edit to its subject. Take it last, after the tree is final, and re-take it if anything changes — a
figure measured against a tree that no longer exists is not a figure. Do not run a second heavy job
alongside a wall-clock measurement."*

### 3. A plan whose deliverable produces an unreviewable PR forfeits its review, and should say so

**Evidence.** Two of this repository's three automated reviewers refused this PR outright — CodeRabbit
at 281 files against a 100-file limit, Sourcery at 317-against-300 when it looked. Review coverage was
**1 of 3**. The claim generalises to runs 2 through 7 **for CodeRabbit only**: its 100-file limit is
below any slice-sized PR. Sourcery's 300 is not — this run's own head ended at 281, inside it — so the
campaign does not guarantee that refusal, and § Reviewer participation records what happened instead.

**Why this is authoring, not execution.** No run can fix it from inside itself: by the time the PR
exists the diff is already the size the deliverable made it. The decision — carve a slice into several
PRs, or accept the forfeit — belongs to whoever shapes the deliverable.

**Proposed edit**, into `author-cloud-plan`: *"A deliverable that produces a pull request larger than
the reviewers' ceilings forfeits most automated review, and no run can recover it. Before writing a
deliverable that touches hundreds of files, either shape it so one run's PR stays inside those ceilings,
or state in the plan that the forfeit is accepted and why. The ceilings are properties of the reviewers,
not of the diff's quality, so a run cannot argue its way past them."*

**Operator decision: pending.** Recorded here so the next run inherits the proposals whether or not
this one gets an answer.

## Residue

### The slice is not finished

By the plan's own § Notes — *"a slice is done when its `test-module-line-budget` count is zero"* —
**run 1 did not finish slice `050`**. Four modules remain, three of them single classes over the budget
and the fourth a 399-line class in a 417-line module whose 18 non-class lines are header, imports and a
banner. Closing them requires splitting a class, which this plan forbids. **A follow-up run cannot fix
them under this plan as written**; the campaign's goal — the rule reaching zero — needs either a
decision to split a class or a stated exemption for a class over the budget. That decision belongs to
whoever owns the flip to `severity: error` (plan `090` § D7's ladder), and is recorded here rather than
taken.

### Stale cross-references this run created and may not fix

⭐ **M16 all but closed this, and that was not why it was done.** Giving 47 sources their name back was
a fix for false module names; the side effect is that a reference naming one of those sources resolves
again. The split now renames away **9** of the 66 sources rather than 56.

⚠️ **The sweep behind the "4 across 2 files" figure only covered `marketplace/`, and that was not
stated.** Widened to `doc/` as well, the count is **at least 9 references across 6 files**, and three of
the five newly-found ones are pointers rather than specimens — they instruct a future run to edit a
module this run deleted:

| File | Names | Kind |
|---|---|---|
| `doc/plans/truthful-signals/550-…-provenance.md:183` | `test_analyze_logs.py`, in a *Done when:* clause | **pointer** |
| `doc/plans/truthful-signals/550-…-provenance.md:415` | `test_analyze_logs.py`, in an Expected-surface entry | **pointer** |
| `doc/plans/code-intelligence-substrate/520-measurement-and-cost-integrity.md:282` | `test_analyze_logs.py` asserts that… | **pointer** |
| `doc/plans/code-intelligence-substrate/550-test-suite-anti-vacuity.md:470` | `test_registered_aspects_render.py:321-404` | specimen (a line range) |
| `doc/plans/test-quality/050-…/plan.md:109` | `plan-retrospective/test_analyze_logs.py (~1,750)` | specimen (a size census) |

Those five sit in **live, unexecuted plan documents** — a future run reading one of them will be told to
edit a file that no longer exists. § Out of scope forbids this plan from editing another plan's
directory, so they are recorded against their owners: the two `truthful-signals` plans, the two
`code-intelligence-substrate` plans, and plan `050`.

The remaining four are not all the same thing, and the report distinguishes them because only one kind
misleads a reader. A **pointer** asserts that a named module keeps something honest; a **specimen** uses
a module name as sample data or as an illustrative example, and is no more broken by the rename than
any other invented path would be. § Out of scope forbids editing `marketplace/bundles/**`, so each is
recorded against its owner rather than fixed. Every prose reference **inside** the slice was repointed
(`cross_file_refs.py` reports 0 remaining).

| File | Names a module that no longer exists | Kind | Owner |
|---|---|---|---|
| `plan-marshall/skills/phase-4-plan/SKILL.md:113, :127, :128` | `test_findings_store.py` as the worked example of the basename-collision naming rule | specimen ×3 | `090` |

⚠️ **This table listed a fourth row — `plan-retrospective/SKILL.md:178` → `test_registered_aspects_render.py`
— and a paragraph built on it reading "the one surviving pointer is the kind that matters most". Commit
`2e2b7d0`, whose entire subject is that pointer, fixed it, and the section still described the tree as
it stood before.** That is precisely M31's class — a disclosure a reader cannot act on — re-created
after M31 closed it, and it is the second time in this report a later commit re-staled a section that
had just been repaired. `SKILL.md:178` now resolves; **the surviving out-of-surface references are three
specimens in one file, and no live pointer.** The split now renames away **8** of the 66 sources.

⚠️ **The one surviving pointer is the kind that matters most**, and it is the last of a class this
report opened with eleven of. It is a note whose whole purpose is to tell a later author which test
keeps a restatement honest, and a note pointing at a file that does not exist is worse than no note: it
reads as a live guarantee and cannot be followed. The two production-code entries that led this table —
the `_EXPLORATION_BUCKETS` and `EXECUTION_LOG_PHASES` hand-mirror notes — resolve again, because
`test_manage_metrics.py` and `test_check_routing_decisions.py` are back.

⚠️ **Eleven in-slice string literals were recorded here as residue and are not residue at all.** Every
module they name exists again: `_consult_fixtures.py:68` → `test_consult.py`, `_planning_lane_fixtures.py:154`
and `_planning_lane_request_body_fixtures.py:148` → `test_planning_lane.py`, three in the
`test_footprint_oracle_classification_*` modules → `test_check_routing_decisions.py`, and five in the
`plan-retrospective/fixtures/` corpus → `test_collect_fragments.py`. All five names are among the 57 M16
restored — which the paragraph above already says for one of them. **There are zero in-slice references
to any of the nine names the split does rename away.** The paragraph is kept, struck through by this
note, because the reasoning it records is still the reason those literals were not touched:
The prose sweep repointed every reference it could reach; a literal it deliberately did not touch,
because changing a string a test asserts on is a semantic edit and not a move. Each is a specimen:
`_consult_fixtures.py:68`'s `TEST_PATH` is the *unmapped* path a consult run must not resolve;
`_planning_lane_fixtures.py:154` and `_planning_lane_request_body_fixtures.py:148` are lines of a
synthetic plan-spec body; three occurrences in the two `test_footprint_oracle_classification_*` modules
are arbitrary paths written into a fake diff; and five sit in the `plan-retrospective/fixtures/`
archived-plan corpus, which is captured input. **None asserts that a file exists**, and repointing them
would change what each test drives. Recorded so the next reader does not mistake the silence for
absence.

### Epic-brief figures this run makes stale

`doc/plans/test-quality/README.md` carries three figures the campaign moves, all already labelled leads
by that document's own "every number is a lead" rule: § "House style" says the budget count is 313 (now
**259**); the executed-half table says `050` has 60 over budget (now **4**); § "The census" says ~309
files exceed 400 lines. This plan writes nothing outside its own directory, and § "Where a recorded
finding goes" assigns a document disagreeing with another to plan `120`.

### Pre-existing findings inside the slice

Recorded in § Findings with plan `050`'s residue as owner: three tests whose rationale a cold reader
cannot recover, a docstring naming a config path its fixture does not write, a hand-parsed TOON helper
whose header-skip does not match the writer's form, bare literals asserted as contracts with no shared
constant, two byte-identical constants, a dead assignment, an unused local, and an undocumented autouse
fixture that defeats the production guard it patches.

### For the next campaign run

Run 2 takes plan `040`'s slice — the delivery pipeline, **55** modules over budget by this run's
derivation. Before starting it, re-derive D1 (this run's own numbers are leads by the same rule that
made the plan's stale) and look plan `100` up in the epic README § "The collision matrix", which names
`110` against whichever slice the campaign is running.

The splitter this run built is not committed — it lives in the session's scratch directory and is gone
with the VM. A run 2 that wants it rebuilds it from § D2 and § D4 of this report, which state the
partition rule, the naming rule, the hoist rules and the four checks that must pass before a byte is
written. **The checks matter more than the tool**: every defect this run shipped and then caught was
caught by one of them or by a reader, and none by the build.

## Appendix — the cold read, verbatim

§ Verification requires the answers recorded verbatim, not just the verdicts. This is the **second**
read, taken against the tree as shipped. The first read's subject tree was superseded by the fixes in
§ Findings; its verdicts and the findings it produced are recorded there.

The reader was given six files and nothing else — three split modules and their
`_{domain}_fixtures.py` — and asked of ten named tests: what contract does this test pin, and why does
it matter?

**A. `TestManifestParsing::test_execution_log_rows_are_read_from_the_manifest` — RECOVERABLE.**
*(a)* `_ledger.load_execution_log(plan_dir)` returns `(rows, reason)`; on a well-formed `execution.toon`
it returns a non-`None` row list with `reason == ''`, and `_ledger.execution_rows_for_phase(rows, phase)`
filters those rows by phase preserving `step_id`. The pin is really that the *reader* parses the tabular
`execution_log[N]{cols}:` bytes the *production writer* (`serialize_toon`) emits.
*(b)* "A hand-written shape would let these tests pass against a form nothing emits — and the first
draft of this helper did exactly that, guessing a dotted `execution_log.0.step_id` layout the writer
never emits." If the reader/writer formats drift, `load_execution_log` returns zero rows against a
manifest that is full, and the reconciliation compares the boundary ledger against an empty side.
*Caveat: every word of that rationale is in `_ledger_reconciliation_fixtures.py`, not the test module.*

**B. `TestDivergentRowsProduceFindings::test_a_boundary_row_with_no_execution_log_row_is_a_finding` — RECOVERABLE.**
*(a)* A dispatch-boundary row with no partner row in a readable execution log produces exactly one
finding of kind `row_absent_from_execution_log`, carrying `phase` and the row's `total_tokens`.
*(b)* "Spend recorded at the dispatch boundary that no execution_log sum sees." The two ledgers are
"written by independent call sites with no shared transaction and no shared key". If this stops
holding, 90k tokens of real spend is invisible to any total derived from `execution_log`.

**C. `TestTheTwoPartialityShapes::test_a_never_closed_phase_is_labelled_distinctly_from_an_absent_row` — RECOVERABLE.**
*(a)* A phase started but never ended, holding boundary rows, produces one `boundary_never_closed`
finding naming `end_time` — *and, separately, simultaneously* — the orphan row finding. Neither absorbs
the other.
*(b)* "Collapsing them would report a whole unclosed phase as a pile of orphan rows, hiding that the
ROWS are present and that what no close recorded is the phase's own summary of them."

**D. `TestTheTwoPartialityShapes::test_a_re_entered_phase_is_its_own_shape` — RECOVERABLE.**
*(a)* A phase closed twice produces exactly one `phase_re_entered` finding whose `detail` contains
`'cumulative across closes'` — a third kind, not folded into the other two.
*(b)* "The aggregate is cumulative, the ledgers are not." Two closes at 1000 and 2000 leave a phase
aggregate of 3000 against a single 1000-token boundary row; without the distinct shape that structural
2000 gap reads as a genuine divergence, so every re-entered phase manufactures a false finding.
*Thin spot: nothing explains why `detail` must carry that exact literal rather than a structured field.*

**E. `TestAdmission::test_default_max_slots_is_five` — UNRECOVERABLE.**
*(a)* With no `marshal.json`, `run_acquire` admits five holders and blocks the sixth, each result
echoing `max_slots: 5`.
*(b)* Not recoverable. Nothing says why the bound is five or what five is a property of; the
justification is outsourced to `solution_outline.md D5`, `lock-reconciliation-analysis.md §5` and
`ADR-002`, none of whose content is present. "A reader cannot tell what breaks if the default drifts to
2 or 20 — one direction serializes a cluster, the other thrashes a host."

**F. `TestIdempotentAcquire::test_re_acquire_blocked_plan_keeps_fifo_position` — RECOVERABLE.**
*(a)* A blocked plan re-acquiring gets its existing id back, stays `blocked`, adds no second waiting
entry, and the persisted order is unchanged.
*(b)* The waiter must not be "shuffled to the back of the queue on each poll." Since `blocked` is a
polling signal rather than an error, re-enqueueing on each poll starves the head of the queue.

**G. `TestRelease::test_run_log_is_pruned_to_most_recent_100_entries` — RECOVERABLE.**
*(a)* After each real release the `run_log` is truncated to its most recent 100 entries; across 150
cycles it holds exactly the last 100 ids in append order.
*(b)* "A bounded audit tail … so a long-lived cluster cannot let build-queue.json grow indefinitely."
That file is machine-global and rewritten under a serialized read-modify-write on every operation.
*Minor gap: why 100 rather than another bound is unstated, but the purpose of the bound is stated.*

**H. `TestFaultPaths::test_missing_fragments_file_errors` — UNRECOVERABLE.**
*(a)* Only partly: the body pins `not result.success` and nothing else — no exit code, no message, no
assertion that no report was written.
*(b)* Not recoverable. `TestFaultPaths` has no docstring and both module docstrings in the pair are the
same seven-word line. "Presumably a missing bundle must not yield a hollow-but-plausible
`quality-verification-report.md` … But that is my reconstruction, not anything the files say."

**I. `TestSessionIdPassthrough::test_session_id_default_string_when_missing` — UNRECOVERABLE.**
*(a)* With `--session-id` omitted, the report contains the literal `session_id: not provided`.
*(b)* Not recoverable. Nothing says what the header `session_id` is for, who reads it, or why absence
needs a sentinel rather than an omitted line. *Additional defect: unlike its sibling, this test discards
`run_script`'s return and never asserts `result.success`.*

**J. `TestRegistryConsistencyGuard::test_render_set_and_accept_set_are_identical` — RECOVERABLE.**
*(a)* The consumer-render key set — every non-`_` `fragment_key` in `retro_sections.SECTION_SPEC` — is
exactly the producer-accept set `valid_aspect_keys()`, in both directions.
*(b)* "The silent-section-drop hole." If they drift, either an aspect a producer may submit renders no
section, or a section the report expects can never be populated. "Both fail quietly at runtime."

**Verdict: 7 of 10 RECOVERABLE.** Unrecoverable: **E**, **H**, **I** — each established in § Findings as
a pre-existing gap, by comparing the test's source byte for byte across the move.
