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

66 modules become **201 test modules** plus **59 `_{domain}_fixtures.py`** modules.

**Class boundaries are the cluster boundaries.** Every module with test classes was split on them; no
class was split. Where a module carried loose top-level `test_` functions, those are the clusters.
Modules are named for the behaviour their clusters share, never for position — the standard's own
counter-example is `test_resolver_part2.py`, and the run's first naming pass produced ten such names
before the labeller was changed to walk more specific candidates instead of appending an ordinal.

**Single-class exceptions — four, named with their line counts** as the plan requires. Each exceeds
the 400-line budget on its own, so leaving it whole is the plan's stated exception rather than a
licence to split a class:

| Class | Lines | Now in |
|---|---:|---|
| `TestDispatchBoundaryContextLoadColumns` | 528 | `plan-retrospective/test_analyze_logs_dispatch_boundary_context_load_columns.py` |
| `TestCmdListStalled` | 426 | `manage-lessons/test_list_stalled.py` |
| `TestCmdRestoreFromPlan` | 424 | `manage-lessons/test_restore_from_plan.py` |
| `TestPhase5LoggingGapExtractors` | 406 | `plan-retrospective/test_analyze_logs_phase5_logging_gap_extractors.py` |

The plan records exactly one such class for the `060` slice and labels the count HYPOTHESIS for every
other. For `050` the count is **four**, of which one (`TestLiveWorktreeReclaimGuard`, 363 lines) was
*not* an exception: it fits the budget, and only the replicated module docstring pushed its module
over. That one is carried with the docstring's summary line alone, so it is inside the budget and the
rest of that prose stays in its sibling modules.

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
| Comments (distinct texts lost) | 8182 | 8663 | **0 lost** |
| `Class::test` multiset | 3970 | 3970 | **0 lost, 0 gained** |
| Non-blank non-comment lines (distinct lost) | 67866 | 73934 | **0 lost** |
| Collected items (slice) | 4207 | 4207 | identical |
| Distinct node ids (slice) | 3822 | 3822 | identical |

**Every difference accounted for.** The comment count *rises* by 481 across the slice: an output module
carries its source's header and import statements, so a comment inside the module docstring is
replicated once per output. The count rose by 719 in an earlier pass, and the extra 238 were the comment
*blocks* sitting between imports being replicated too — that also multiplied one
`test-docstring-historical-prose` finding into three. Output modules now take the import statements
alone and the commented block survives whole in the fixtures module, which returned that rule to its
pre-split count.

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
| Test modules in slice | 209 | 345 | +136 | `Path.rglob('*.py')` over the slice, `test_*` only |
| `.py` files in slice | 215 | 414 | +199 | same, all `.py` |
| Collected items, slice | 4207 | 4207 | 0 | `uv run python -m pytest {slice} -o addopts= --collect-only -q` |
| Comments in slice | 7967 | 8448 | +481 | `tokenize`, `COMMENT` tokens |
| Lines in slice | 90928 | 99708 | **+8780 (+9.7%)** | `len(read_text().split('\n'))` |
| Coverage, slice bundle paths | 89% | 89% | 0 | `pytest {slice} --cov={10 skill script dirs} --cov-report=term` |

Coverage is not merely non-decreasing but **identical**: 9986 statements, 962 missed, 3682 branches,
355 partial, both sides.

**The line delta is an observation, not a target.** +9.7% **confirms** the plan's HYPOTHESIS that
splitting is line-neutral to slightly positive; it is not a refutation, and nothing was deleted to
improve it. The growth is a header and an import block per new module, which is the cost the plan
predicted and priced in when it refused a line floor.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty — this run changes Python — so the
full gate applies.

_verify pending_

## Findings

_pending_

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
