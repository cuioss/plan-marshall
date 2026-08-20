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

**Done.** The file set was derived from the D1 attribution — the 66 modules the sweep named as over
budget within `050`'s Expected surface — never from a tree walk. The check that the changed set stayed
inside that surface is the sweep itself: re-run whole-tree after the split, **every other slice's count
is unchanged** (`030` 40, `040` 55, `060` 53, `070` 61, `080` 42, row 7 = 1). A stray edit outside the
surface would have moved one of them. An independent verification pass re-derived the whole
attribution against the six plans' own Expected surfaces and reproduced D1's table exactly.

66 modules become **199 test modules** plus **64 `_{domain}_fixtures.py`** modules. (The slice held 209
test modules before and holds 342 now; 143 were never over budget and are untouched, so 342 − 143 = 199
is what the 66 became. 189 of those 199 carry a new name; the other 10 are modules that hoisting alone
brought inside the budget, which keep the name their readers already know. The `.py` file count goes
215 → 412.)

**Class boundaries are the cluster boundaries.** Every module with test classes was split on them; no
class was split. Where a module carried loose top-level `test_` functions, those are the clusters.
Modules are named for the behaviour their clusters share, never for position — the standard's own
counter-example is `test_resolver_part2.py`, and the run's first naming pass produced ten such names
before the labeller was changed to walk more specific candidates instead of appending an ordinal.

**Four modules remain over budget**, and they are two different things. The plan's stated exception is
"a class larger than the budget", so they are reported split by whether the class actually is:

| Class | Class lines | Module lines | Over budget alone? | Now in |
|---|---:|---:|---|---|
| `TestDispatchBoundaryContextLoadColumns` | **495** | 536 | **yes** — the plan's exception | `plan-retrospective/test_analyze_logs_dispatch_boundary_context_load_columns.py` |
| `TestCmdListStalled` | **424** | 466 | **yes** | `manage-lessons/test_list_stalled.py` |
| `TestCmdRestoreFromPlan` | **422** | 465 | **yes** | `manage-lessons/test_restore_from_plan.py` |
| `TestPhase5LoggingGapExtractors` | 399 | 417 | **no** — the class fits, by one line | `plan-retrospective/test_analyze_logs_phase5_logging_gap_extractors.py` |

The plan records exactly one budget-exceeding class for the `060` slice and labels the count HYPOTHESIS
for every other slice. For `050` it is **three**.

The fourth is a distinct shape the plan does not name, and this report does not fold it into the
exception: the class is inside the budget and the *module* is not, because a module also carries a
header, an import block and a banner comment. `TestPhase5LoggingGapExtractors` misses by 18 lines
against a 399-line class, and those 18 are the header, the imports and the banner — verified
irreducible, with no slack left to find. The class cannot be split, so the module stays as it is.

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
(`_ledger_reconciliation_fixtures.py`), not per directory. `manage-metrics/` alone holds 13 over-budget
modules whose preambles bind the same names to different values; merging them into one
`_manage_metrics_fixtures.py` — which already exists, with its own contents — would have required
renaming references across the directory, which is a semantic edit, not a move. Per-source hoisting
also keeps each script load executing once rather than once per output, which is the mechanism the
epic names as most likely to make this campaign the one that slows the suite. `unique-fixture-basenames`
and `test-helper-module-misnamed` both remain at 0, so the naming satisfies the enforced rules.

**One `@pytest.fixture` exception to the hoist, and its cost is stated.** A fixture stays in the modules
that consume it. Moving one to the fixtures module and importing it costs two suppressions: `F401` on
the import, because a fixture is never used *as* a name, and a module-level `# ruff: noqa: F811` for
every test that takes it as a parameter — F811 is reported at the parameter, out of reach of a `noqa`
on the import, so only a module-level directive reaches it. That directive disables the check for a
whole module, which is a real cost, so it is paid only where keeping the fixture inline would push a
module past the budget. **Exactly one module qualifies** (above).

Everywhere else the fixture is duplicated into the outputs that consume it, closed over
fixture-to-fixture dependencies. **The magnitude, which an earlier draft of this report understated
and transposed:** 13 distinct fixture names are duplicated into **48 extra copies**, taking the slice's
module-level fixture definitions from **40 to 88**. Every copy is byte-identical today, so nothing has
diverged — but it is a drift surface this run created and it is priced here rather than left implicit.

### D3 — Preserve every shared registration through the move

**Done, and the answer is the strong one: this run changed no registration name at all.**

Every `load_script_module` / `spec_from_file_location` call moved **whole** into its module's fixtures
module, carrying its own registration name with it. No two previously-distinct registrations were
collapsed onto a shared one, which is the mechanism that cost plan `030` 173 order-dependent failures.
The report therefore names **no** registration whose name this run changed, and the "demonstrably free
of module-level mutable state" evidence the plan asks for alongside such a change is not owed, because
no such change was made.

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
size to be mistaken for one another. **Population P1** is every `test_*.py` sitting directly in the
eleven affected directories, which is what the move-fidelity diff compares. **Population P2** is the
whole slice as § Expected surface defines it — the ten directories recursively plus the three
root-level modules — which is what the deltas in D5 count.

| Measure | Population | Before | After | Verdict |
|---|---|---:|---:|---|
| Comment texts absent at HEAD | P1 | 8182 | 8672 | **22 absent, 0 unexplained** (below) |
| `Class::test` occurrences | P1 | 3970 | 3970 | **0 lost, 0 gained** |
| Non-blank non-comment lines absent at HEAD | P1 | 67866 | 71375 | **58 absent, 0 unexplained** (below) |
| Collected items | P2 | 4207 | 4207 | identical |
| Distinct `Class::test` ids | P2 | 3822 | 3822 | identical |

⚠️ **"Nothing lost" stopped being the right measurement once this run began deliberately rewriting
prose.** 22 comment texts and 58 code lines present before the split are absent at HEAD. A bare count
there is not evidence either way, so each absence is **classified**, and the number that means a text
was lost is the residue:

| Why a text is absent at HEAD | Comments | Code lines |
|---|---:|---:|
| A directional reference this run deliberately rewrote (M2) | 22 | 8 |
| The docstring reframe moved the opening `"""` — the text survives verbatim one line down (M10) | 0 | 43 |
| `ruff --fix` rewrote an import whose names the split left partly unused | 0 | 7 |
| **UNEXPLAINED** | **0** | **0** |

**Every difference accounted for.** The comment count *rises* by 472 across the slice: an output module
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
| `test-module-line-budget`, slice `050` | 66 | **4** | −62 | `{DOCTOR} --test-root test/`, grouped by slice |
| `test-module-line-budget`, whole tree | 318 | **256** | −62 | `{DOCTOR} --test-root test/` |
| Test modules in slice | 209 | 342 | +133 | `Path.rglob('*.py')` over the slice, `test_*` only |
| `.py` files in slice | 215 | 412 | +197 | same, all `.py` |
| Collected items, slice | 4207 | 4207 | 0 | `uv run python -m pytest {slice} -o addopts= --collect-only -q` |
| Distinct `Class::test` ids, slice | 3822 | 3822 | 0 | `ast`, class/function walk |
| Comments in slice | 7967 | 8457 | +490 | `tokenize`, `COMMENT` tokens |
| Lines in slice | 90928 | 96897 | **+5969 (+6.6%)** | `len(read_text().split('\n'))` |
| Coverage, slice bundle paths | 89% | 89% | 0 | see the command below |

**The coverage command in full**, because an earlier draft named only "{10 skill script dirs}" and was
not reproducible as written. `{B}` is `marketplace/bundles/plan-marshall/skills`:

```bash
uv run python -m pytest {slice} -o addopts= -q -p no:randomly \
  --cov={B}/audit-archived-plan-retrospectives --cov={B}/manage-adr \
  --cov={B}/manage-change-ledger --cov={B}/manage-findings --cov={B}/manage-lessons \
  --cov={B}/manage-locks --cov={B}/manage-metrics --cov={B}/manage-status \
  --cov={B}/manage-tasks --cov={B}/plan-retrospective --cov-report=term
```

**The line delta is an observation, not a target.** +6.6% **confirms** the plan's HYPOTHESIS that
splitting is line-neutral to slightly positive; it is not a refutation, and nothing was deleted to
improve it. The growth is a header and an import block per new module, which is the cost the plan
predicted and priced in when it refused a line floor.

It was **+9.7%** before the docstring change described under M1: replicating each source's whole
docstring into every output was the single largest contributor, and keeping the full text once in the
fixtures module removed about 2,700 lines while making each output's docstring true of that output.
The number moved because a defect was fixed, not because it was chased.

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
| M2 | 29 directional references falsified across 19 files: a comment reading "the test below" was true while helper and tests shared a module, and points at nothing once the helper is hoisted | Cold read items 4–6; sweep of the 63 new fixtures modules | **Fixed** — each rewrite drops the direction and keeps the claim. Directional words still true (a markdown heading's body, a magnitude, a numeric threshold, a symbol genuinely above in the same file) were checked individually and kept |
| M3 | Module names truncated to a character budget, ending mid-phrase — `_is_absent_rather_than`, `_stale_legacy_key_without`, `_does_not_claim`. 71 of the generated names exceeded 52 characters | Name sweep of the generated set | **Fixed** — candidates are built from whole meaningful words and a name repeating the unit it already carries has the repetition dropped. 19 names remain over 52 characters; none is truncated |
| M4 | **Seven tests silently lost.** Two bins of one module resolved to the same filename; `render()` keys its output by filename, so the second write replaced the first and every test in the first disappeared | `verify_move.py` reported `tests lost=7`, all from `test_manage_locks_merge_lock.py` (`TestIdempotentRepoll`, `TestReleaseAdvancesFront`) | **Fixed** — the name search widens until unique, and a duplicate is now an assertion rather than a silent overwrite |
| M5 | The fixtures module grouped every import ahead of every statement, moving a `sys.path.insert` **after** the import it enables | Cold read item 3 | **Fixed** — regions are emitted in source order, imports and statements interleaved |
| M6 | A compacted docstring was cut at its first physical **line**; these docstrings wrap, so the module's own description ended mid-sentence (`…the first-class`) | Scan for docstrings not ending in terminal punctuation | **Fixed** — compaction keeps the summary **paragraph** |
| M7 | `test-module-preamble-boilerplate` rose 100 → 102: two modules whose shared preamble sat just under the hoisting threshold duplicated a `spec_from_file_location` block into each output | Whole-tree sweep diff | **Fixed** — threshold lowered so the loader lands in a fixtures module, as D2 directs. Back to 100 |
| M8 | `test-docstring-historical-prose` rose 200 → 203: comment blocks *between imports* were replicated into every output, multiplying a citation | Whole-tree sweep diff, per-file | **Fixed** — outputs take import statements only; the commented block survives whole in the fixtures module |
| M9 | `test-docstring-historical-prose` rose 200 → 201: a **non-splitting** module keeps its own full docstring, and the fixtures module copied it, duplicating the citation it carries | Whole-tree sweep diff, `manage-status` 2 → 3 | **Fixed** — the fixtures module carries the full docstring only when the outputs are compacted |

| M10 | M1's fix **relocated** the over-claim rather than removing it: the inherited docstring now heads a fixtures module, which contains no tests, while still opening "Tests for ``x.py``" and enumerating a contract. The second cold read called it "the largest over-claim", listing six contract bullets whose tests are in sibling modules | Second cold read, Q2 | **Fixed** — the inherited text is *framed*, not edited: a lead-in states what the file is and whose contract the text below pins, and the original prose follows unchanged. 54 of 63 fixtures modules carry an inherited docstring; the other 9 already had a generated one |

| M11 | A preamble too small to hoist was **duplicated** into each output — and where it loads a script, that registers the same `sys.modules` key from three files and hands the siblings three distinct module objects racing one name. `compile-report`'s `cr_behavior_mod` had one registration on `main` and three after the split | Independent verification pass, trap 2 follow-through | **Fixed** — a preamble that loads a script is hoisted whatever its size. One registration again |
| M12 | D2's stated reason for keeping every fixture inline — that `F811` "is reported at the parameter, so no `noqa` on the import can reach it" — is **false**. A module-level `# ruff: noqa: F811` reaches it, and this repo already uses that pattern. The false claim was the justification for leaving a module over budget | Independent verification pass; `test_phase_handshake_phase_steps.py:3` | **Fixed** — the claim is corrected and the module hoists its fixtures, falling 432 → 387 lines |
| M13 | The M2 sweep missed five instances of its own defect class: comments reading "the autouse fixture below" in fixtures modules that hold no fixture at all | Independent verification pass, finding D | **Fixed** — 34 directional references now corrected across 20 files, up from 29 |

Every one of M7–M9 was found by re-measuring **all seven** rules whole-tree rather than only the one
this plan targets. The final sweep has `test-module-line-budget` at 256 and the other six at exactly
their pre-split values.

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

For the third pair the reader reported the premise did not even hold: `_compile_report_fixtures.py`'s
docstring is byte-identical to its test module's — both are the same seven-word line — so there the
problem is not misplaced rationale but absent rationale, which is a pre-existing gap.

### Pre-existing, recorded not fixed

The cold read (§ Verification, "By reading") found **6 of 10** tests recoverable. The four that were
not are **pre-existing**, and that is established mechanically rather than asserted: each test's
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
| An undocumented autouse fixture (`_seed_guarded_plan_dirs`) that monkeypatches production `require_plan_exists` to *create* the directory it guards, with no docstring saying why | `050` residue |
| Stale external pointers with no in-repo target (`solution_outline.md D5`, `lock-reconciliation-analysis.md §5`, `ADR-002`, `Task-4 coverage`, two bare commit hashes) | `050` residue (prose) |
| `test_session_id_default_string_when_missing` discards `run_script`'s return and never asserts `result.success`, unlike its sibling one test above it — a script failing before the write would surface as a confusing file mismatch rather than the real error | `050` residue |
| `test_missing_fragments_file_errors` asserts only `not result.success` — no exit code, no message, and no assertion that no report was written, which is the half that matters if a missing bundle could yield a hollow-but-plausible report | `050` residue |

**Filename-versus-content drift, and it is partly this run's:** the cold read noted that
`test_ledger_reconciliation_manifest_parsing.py` holds one manifest-parsing test out of ten, and that
`test_compile_report_fault_paths.py` ends with a registry-consistency guard that is not a fault path.
That is the naming rule's limit rather than a bug in it: a bin is named for the behaviour its clusters
share, and where adjacent clusters share none the name describes the bin's leading cluster. It is
disclosed here rather than fixed, because the alternative — regrouping clusters by theme across the
module — reorders tests between files and is a larger change than this deliverable licenses.

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

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence |
|---|---|---|---|
| `cuioss-review-bot` | `reviewed` | — | Published a review against the diff: *"PR contains tests · No security concerns identified · No major issues detected"* |
| `coderabbitai` | `rate-limited` | **no** | *"Review skipped — Too many files! This PR contains 317 files, which is 217 over the limit of 100. To get a review, reduce the PR to 100 files or fewer…"* |
| `sourcery-ai` | `rate-limited` | **no** | *"Sorry, we are unable to review this pull request. The GitHub API does not allow us to fetch diffs exceeding 300 files, and this pull request has 317"* |

**Coverage: 1 of 3.** The § Step 8 condition 5 disclosure fired and said exactly that.

⚠️ **Neither refusal is a clock, and that is the whole point.** Both are ceilings on *this diff's size* —
100 files for one reviewer, 300 for the other — so `Reopens? no`: no wait, no retry and no jitter
schedule can change them, and the lane's retry budget does not apply. Condition 6 is satisfied on its
`Reopens? no` arm rather than by spending attempts against a mechanism that cannot deliver.

⛔ **This is a structural finding about the campaign, not an incident on one PR.** A slice split
produces a PR of roughly this size by construction — 66 sources became 263 files here — so **runs 2
through 7 will each be refused by the same two reviewers for the same reason**. Two thirds of this
repository's automated review capacity is unreachable for the campaign as the plan currently shapes a
run, and no run can fix that from inside itself: the remedy is a plan-level decision about how a slice
is carved into pull requests. It is recorded in § Residue and raised to the operator rather than
absorbed.

The inline review-thread surface (`get_review_comments`) returned an empty set and the read succeeded,
so that is a genuine absence rather than an unreadable surface. All three surfaces were read.

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

_pending_

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

The split renamed 58 of the 66 sources, and 12 references to the old names survive **outside** this
plan's Expected surface. § Out of scope forbids editing `marketplace/bundles/**` and any directory
outside the slice, so each is recorded against its owner rather than fixed. The 39 references **inside**
the slice were repointed.

| File | Names a module that no longer exists | Owner |
|---|---|---|
| `plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` | `test_manage_metrics.py` — an `_EXPLORATION_BUCKETS` hand-mirror note naming the test that holds it honest | `090` |
| `plan-marshall/skills/plan-retrospective/scripts/check-routing-decisions.py` | `test_check_routing_decisions.py` — an `EXECUTION_LOG_PHASES` mirror note | `090` |
| `plan-marshall/skills/manage-metrics/SKILL.md` | `test_manage_metrics.py` | `090` |
| `plan-marshall/skills/manage-lessons/SKILL.md` | `test_consult.py` | `090` |
| `plan-marshall/skills/manage-status/SKILL.md` | `test_planning_lane.py` | `090` |
| `plan-marshall/skills/phase-4-plan/SKILL.md` | `test_findings_store.py`, `test_qgate_closure.py` | `090` |
| `plan-marshall/skills/plan-retrospective/SKILL.md` | `test_registered_aspects_render.py` | `090` |
| `test/plan-marshall/manage-execution-manifest/test_plan31_docs_only_deadlock_regression.py` | `test_pre_commit_verify_freshness.py` | `030` |
| `test/plan-marshall/phase-2-refine/test_phase_2_refine_manage_config_readonly.py` | `test_manage_status_transition.py` | `070` |
| `test/plan-marshall/phase-5-execute/test_phase5_change_ledger.py` | `test_manage_change_ledger.py` | `040` |
| `test/plan-marshall/phase-6-finalize/test_loop_back_outcome.py` | `test_mark_step_done.py` | `040` |
| `test/plan-marshall/tools-script-executor/test_build_class_stamp_discriminator.py` | `test_freshness_notation_crosscheck.py` | `060` |

⚠️ **The two production-code entries are the ones that matter most.** Both are hand-mirror notes whose
whole purpose is to tell a later author which test keeps a duplicated constant honest. A note pointing
at a file that does not exist is worse than no note: it reads as a live guarantee and cannot be
followed. They are recorded first for that reason.

### Epic-brief figures this run makes stale

`doc/plans/test-quality/README.md` carries three figures the campaign moves, all already labelled leads
by that document's own "every number is a lead" rule: § "House style" says the budget count is 313 (now
**256**); the executed-half table says `050` has 60 over budget (now **4**); § "The census" says ~309
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
