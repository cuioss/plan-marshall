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
surface would have moved one of them.

66 modules become **199 test modules** plus **63 `_{domain}_fixtures.py`** modules. (The slice held 209
test modules before and holds 342 now; 143 were never over budget and are untouched, so 342 − 143 = 199
is what the 66 became. The `.py` file count goes 215 → 411, and 69 − 6 = 63 of the difference is the
new fixtures modules.)

**Class boundaries are the cluster boundaries.** Every module with test classes was split on them; no
class was split. Where a module carried loose top-level `test_` functions, those are the clusters.
Modules are named for the behaviour their clusters share, never for position — the standard's own
counter-example is `test_resolver_part2.py`, and the run's first naming pass produced ten such names
before the labeller was changed to walk more specific candidates instead of appending an ordinal.

**Five modules remain over budget, and they are two different things.** The plan's stated exception is
"a class larger than the budget", so the five are reported split by whether the class actually is:

| Class | Class lines | Module lines | Over budget alone? | Now in |
|---|---:|---:|---|---|
| `TestDispatchBoundaryContextLoadColumns` | **495** | 537 | **yes** — the plan's exception | `plan-retrospective/test_analyze_logs_dispatch_boundary_context_load_columns.py` |
| `TestCmdListStalled` | **424** | 467 | **yes** | `manage-lessons/test_list_stalled.py` |
| `TestCmdRestoreFromPlan` | **422** | 466 | **yes** | `manage-lessons/test_restore_from_plan.py` |
| `TestLiveWorktreeReclaimGuard` | 355 | 432 | **no** — the class fits | `manage-locks/test_manage_locks_merge_lock_live_worktree_reclaim_guard.py` |
| `TestPhase5LoggingGapExtractors` | 399 | 418 | **no** — the class fits, by one line | `plan-retrospective/test_analyze_logs_phase5_logging_gap_extractors.py` |

The plan records exactly one budget-exceeding class for the `060` slice and labels the count HYPOTHESIS
for every other slice. For `050` it is **three**.

The last two are a distinct shape the plan does not name and this report does not fold into the
exception: the class is inside the budget and the *module* is not, because a module also carries a
header, an import block and the pytest fixtures its tests consume. Those fixtures cannot be hoisted —
importing one puts its name where ruff reads a redefinition at the consuming parameter — and the
class cannot be split, so neither module can be brought under 400 by anything this deliverable
permits. `TestPhase5LoggingGapExtractors` misses by 18 lines against a 399-line class; there is no
slack left to find.

Both are inside the budget on the measure the epic actually cares about — the class is nameable and
whole — and both are reported here rather than quietly counted as class exceptions.

**Deviation from D2's letter, stated rather than absorbed.** D2 says shared helpers, constants and
loaders "move into a `_{domain}_fixtures.py`". This run hoists **per source module**
(`_ledger_reconciliation_fixtures.py`), not per directory. `manage-metrics/` alone holds 13 over-budget
modules whose preambles bind the same names to different values; merging them into one
`_manage_metrics_fixtures.py` — which already exists, with its own contents — would have required
renaming references across the directory, which is a semantic edit, not a move. Per-source hoisting
also keeps each script load executing once rather than once per output, which is the mechanism the
epic names as most likely to make this campaign the one that slows the suite. `unique-fixture-basenames`
and `test-helper-module-misnamed` both remain at 0, so the naming satisfies the enforced rules.

**One `@pytest.fixture` exception to the hoist.** A fixture stays in the modules that consume it. Moving
one to the fixtures module and importing it puts its name where ruff reads a redefinition twice over:
`F401` on the import, because a fixture is never used *as* a name, and `F811` on every test method that
takes it as a parameter. `F811` is reported at the parameter, so no `noqa` on the import can reach it.
Keeping the fixture beside its consumers is also what the module did before the split. 24 fixtures
across 14 modules are handled this way, closed over fixture-to-fixture dependencies.

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

| Measure | Before | After | Verdict |
|---|---:|---:|---|
| Comments (distinct texts lost) | 8182 | 8653 | **0 lost** |
| `Class::test` multiset | 3970 | 3970 | **0 lost, 0 gained** |
| Non-blank non-comment lines (distinct lost) | 67866 | 71508 | **0 lost** |
| Collected items (slice) | 4207 | 4207 | identical |
| Distinct node ids (slice) | 3822 | 3822 | identical |

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
subset each module needs). Every name they bound still resolves — checked statically across all 260
rendered modules before writing, and again by the suite.

### D5 — Report the measured deltas

Every figure with the command that produced it. `{DOCTOR}` is the epic README's
`PYTHONPATH`-prefixed `doctor-marketplace.py test-conventions` invocation, used unmodified — the five
directories it names were sufficient, so the next run inherits it unchanged.

| Measure | Before | After | Δ | Command |
|---|---:|---:|---:|---|
| `test-module-line-budget`, slice `050` | 66 | **5** | −61 | `{DOCTOR} --test-root test/`, grouped by slice |
| `test-module-line-budget`, whole tree | 318 | **257** | −61 | `{DOCTOR} --test-root test/` |
| Test modules in slice | 209 | 342 | +133 | `Path.rglob('*.py')` over the slice, `test_*` only |
| `.py` files in slice | 215 | 411 | +196 | same, all `.py` |
| Collected items, slice | 4207 | 4207 | 0 | `uv run python -m pytest {slice} -o addopts= --collect-only -q` |
| Distinct `Class::test` ids, slice | 3822 | 3822 | 0 | `ast`, class/function walk |
| Comments in slice | 7967 | 8439 | +472 | `tokenize`, `COMMENT` tokens |
| Lines in slice | 90928 | 97014 | **+6086 (+6.7%)** | `len(read_text().split('\n'))` |
| Coverage, slice bundle paths | 89% | 89% | 0 | `pytest {slice} --cov={10 skill script dirs} --cov-report=term` |

**The line delta is an observation, not a target.** +6.7% **confirms** the plan's HYPOTHESIS that
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
| M3 | Module names truncated to a character budget, ending mid-phrase — `_is_absent_rather_than`, `_stale_legacy_key_without`, `_does_not_claim`. 71 of 202 names exceeded 52 characters | Name sweep of the generated set | **Fixed** — candidates are built from whole meaningful words and a name repeating the unit it already carries has the repetition dropped. 19 names remain long; none is truncated |
| M4 | **Seven tests silently lost.** Two bins of one module resolved to the same filename; `render()` keys its output by filename, so the second write replaced the first and every test in the first disappeared | `verify_move.py` reported `tests lost=7`, all from `test_manage_locks_merge_lock.py` (`TestIdempotentRepoll`, `TestReleaseAdvancesFront`) | **Fixed** — the name search widens until unique, and a duplicate is now an assertion rather than a silent overwrite |
| M5 | The fixtures module grouped every import ahead of every statement, moving a `sys.path.insert` **after** the import it enables | Cold read item 3 | **Fixed** — regions are emitted in source order, imports and statements interleaved |
| M6 | A compacted docstring was cut at its first physical **line**; these docstrings wrap, so the module's own description ended mid-sentence (`…the first-class`) | Scan for docstrings not ending in terminal punctuation | **Fixed** — compaction keeps the summary **paragraph** |
| M7 | `test-module-preamble-boilerplate` rose 100 → 102: two modules whose shared preamble sat just under the hoisting threshold duplicated a `spec_from_file_location` block into each output | Whole-tree sweep diff | **Fixed** — threshold lowered so the loader lands in a fixtures module, as D2 directs. Back to 100 |
| M8 | `test-docstring-historical-prose` rose 200 → 203: comment blocks *between imports* were replicated into every output, multiplying a citation | Whole-tree sweep diff, per-file | **Fixed** — outputs take import statements only; the commented block survives whole in the fixtures module |
| M9 | `test-docstring-historical-prose` rose 200 → 201: a **non-splitting** module keeps its own full docstring, and the fixtures module copied it, duplicating the citation it carries | Whole-tree sweep diff, `manage-status` 2 → 3 | **Fixed** — the fixtures module carries the full docstring only when the outputs are compacted |

| M10 | M1's fix **relocated** the over-claim rather than removing it: the inherited docstring now heads a fixtures module, which contains no tests, while still opening "Tests for ``x.py``" and enumerating a contract. The second cold read called it "the largest over-claim", listing six contract bullets whose tests are in sibling modules | Second cold read, Q2 | **Fixed** — the inherited text is *framed*, not edited: a lead-in states what the file is and whose contract the text below pins, and the original prose follows unchanged. 54 of 63 fixtures modules carry an inherited docstring; the other 9 already had a generated one |

Every one of M7–M9 was found by re-measuring **all seven** rules whole-tree rather than only the one
this plan targets. The final sweep has `test-module-line-budget` at 257 and the other six at exactly
their pre-split values.

⚠️ **M1, M9 and M10 are the same defect found three times, each time in the place the previous fix put
it.** M1 was the docstring replicated into every output; M9 was the fixtures module copying a docstring
the single output already had; M10 was the inherited docstring heading a file it did not describe. Each
fix was sound where it landed and moved the claim somewhere the next round had to find it. The
deliverables should be read as still carrying defects of that kind.

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
| 2. Coverage does not decrease (slice bundle paths) | 89% | 89% | **holds** — bit-identical: 9986 statements, 962 missed, 3682 branches, 355 partial, both sides |
| 3. Order-independent (default **and** reverse directory order) | — | 4207 passed both | **holds** |
| 4. `EXEMPT_RULE_IDS` unchanged | n/a | n/a | **not applicable** — that check is stated for the `080` slice; this run is `050` and touches no plugin-doctor module |
| 5. Suite not slower, skipped count not higher (whole tree) | 21070 passed, 14 skipped, 1958.89 s | _pending_ | _pending_ |

## Reviewer participation

_pending_

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
