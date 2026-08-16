# Run report — 030-config-and-manifest-test-reduction (run 01)

**Date (UTC):** 2026-08-16    **Branch:** `claude/config-manifest-test-reduction-0eod0y` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** partial — see § Verification verdict

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill:` notation (project-local `.claude/skills/`) |
| `pm-dev-python:pytest-testing` | bundle path — `marketplace/bundles/pm-dev-python/skills/pytest-testing/SKILL.md` |
| `plan-marshall:persona-module-tester` | bundle path (module-budget section, 400 lines) |

`plan-marshall:ref-code-quality` and `pm-plugin-development:plugin-script-architecture` were **not**
loaded: this plan's whole surface is `test/**`, and its Out of scope forbids touching
`marketplace/bundles/**`, so neither skill governs anything this run may edit.

## Gating derivations (run before D1)

### Plans `010` and `020` have landed — CONFIRMED

- `grep -n 'def parse_ns' test/conftest.py` → `569:def parse_ns(...)`.
- Module budget: `persona-module-tester/standards/testing-methodology.md:75` → **400 lines**, enforced
  by `plugin-doctor`'s `test-module-line-budget`.

### Partition check — DEFECT FOUND, dispositioned by the operator

Derived mechanically over every directory under `test/plan-marshall/*/` (69), every file at the root of
`test/plan-marshall/` (12), and every top-level `test/` entry other than `plan-marshall/` (23), each
checked against the Expected surface of `030`–`080`.

- **Duplicates (an entry in two lists): none.**
- **Unclaimed entries: three.**

| Entry | Status |
|---|---|
| `test/README.md` | Claimed by plan `020` (epic README § concurrency table). Not a `.py` file. Not a defect; the README's named-exclusion list is short by this entry. |
| `test/test_shared_harness.py` | Claimed by plan `020` (`020/plan.md:174`, D5 — created by that plan). A fourth de-facto exclusion the README's list does not name. |
| `test/pm-code-intelligence/` | **Claimed by no plan at all.** Added 2026-08-15 by `c86de8b` (PR #1243), *after* the test-quality plans were authored — exactly the failure mode the epic README predicts. One file, 260 lines. |

**Disposition:** the operator was asked and stated the `pm-code-intelligence` gap is handled by another
plan. The halting condition was released by operator decision, not by this run's judgement. This run
claimed nothing outside its six directories.

Line-sum check: corpus `test_*.py` total **387,521**; the six slices sum to **386,879**; the
**642**-line difference is exactly `test/pm-code-intelligence/` (260) + `test/test_shared_harness.py`
(382). No gap and no overlap beyond the three entries above.

### D1 family membership — re-derived, the plan's OBSERVED claim CONFIRMED exactly

Suffixes extracted under each prefix **separately** and intersected, per the plan's instruction:

- `test_default_plan_finalize_includes_*`: **7** functions.
- `test_get_default_config_includes_*`: **15**. Total **22**, matching the lead.
- **Intersection: exactly 3** — `admin_merge_on_stuck_state`, `auto_rebase_threshold`,
  `merge_queue_wait_budget_seconds`. Exactly the plan's named three.

**The higher-risk HYPOTHESIS — "every pair asserts only the same thing" — was tested by reading all 22
bodies before any collapse. It is FALSE, in the run's favour:**

1. Both prefixes reach the knob through the **same** accessor,
   `_params_for(config['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup')`. The plan's
   "two accessors" framing does not hold at the code level; the prefix difference is historical.
2. All **7** `default_plan_finalize` members carry a third assertion the `get_default_config` members
   do not — the `'{knob}' not in DEFAULT_PLAN_FINALIZE` **negative**. It is uniform across all 7, so it
   survives as a body assertion of the collapsed table rather than being dropped.
3. The 3 `get_default_config` members for the crossed knobs assert a strict **subset**. They were kept
   as their own 3-row table rather than deleted, so the collected count is preserved exactly.

## Deliverables

| # | Deliverable | Verdict | Evidence |
|---|---|---|---|
| D1 | Parametrize the contract tables | **Partial** | 11 families collapsed across 3 modules (below). Done-when 1 is met for `test_config_defaults.py`; the slice-wide family population is ~113, and `test_decision_rules.py` — named in D1 — received no table. |
| D2 | Split every module over budget | **Not done** | `test-module-line-budget` 41 → 39. Sequenced after D1 by the plan; D1 did not complete. |
| D3 | Arrange into fixtures and factories | **Not done** | setattr:fixture ratio unchanged at 257:13. No `parse_ns` call sites converted, so the exception list is empty by non-attempt, not by finding none. |
| D4 | One import preamble | **Partial** | 137 → 30 doctor findings (78% closed); 50 modules converted. Done-when (grep returns nothing) **not met**: 22 sites in 15 files remain. |
| D5 | Docstrings state the invariant | **Done** | `test-docstring-historical-prose` 24 → **0** across all six directories. |
| D6 | Report the measured deltas | **Done** | This report; every figure carries its command. |

### D1 — families collapsed (commits `b606c76`, `a848353`, `9e6a1c1`)

| Module | Collapsed family | Functions → cases |
|---|---|---|
| `manage-config/test_config_defaults.py` | `default:branch-cleanup` step-param defaults | 7 → 7 |
| " | `get_default_config` round-trip of the 3 crossed knobs | 3 → 3 |
| " | config-validator rejections (8 validators, one table) | 20 → 20 |
| " | config-validator enum acceptance | 4 → 4 |
| `manage-execution-manifest/test_manage_execution_manifest_compose.py` | `_role_of` canonical→role resolution | 7 → 10 |
| " | `_lane_keep_decision` override matrix | 5 → 5 |
| " | recipe-provenance decision-matrix rows | 6 → 6 |
| `manage-config/test_effort_read.py` | effort-resolution cascade | 10 → 10 |
| " | effort-read rejection cases | 4 → 4 |
| `manage-config/test_config_defaults.py` | `DEFAULT_PLAN_{EXECUTE,INIT}` knob registration | 5 → 5 |
| " | `get_default_config` surfacing of the same five | 5 → 5 (+1 named round-trip test) |

**Two deliberate non-collapses, each recorded rather than silently skipped:**

- `test_flat_group_set_returns_role_value` stays out of the effort cascade table: it carries a
  marshal.json hash-stability assertion the other rungs do not.
- The three `test_init_includes_*` functions in `test_cmd_init.py` share only a name **prefix**. They
  assert three different section contracts, one of which carries an ordering invariant
  (`archive-plan` last, `record-metrics` before it) that a shared table would contort. The plan
  anticipates exactly this — such members "belong in a single-accessor table **or in no table at
  all**" — so they are left alone. Their repeated `cmd_init` + read-marshal arrange **is** a genuine
  B4 fixture candidate, and is left to D3.

### D4 — the isolation hazard this deliverable carries

`conftest.load_script_module` registers the loaded module in `sys.modules` under `module_name`,
defaulting to the script stem. The bespoke preambles this deliverable replaces used **unique** names
(`_config_defaults_for_split_gate_test`), which gave each test module a private copy. The marketplace
config modules carry **mutable module-level default dicts**, so collapsing two test modules onto one
registration name lets one module's mutation leak into another's read.

Dropping those unique names in the first pass produced **173 failures**, all order-dependent and all
passing in isolation (e.g. `test_plan_q_gate_validation_get_returns_once_default` read `'off'` for a
knob defaulting to `'once'`). Every converted call now preserves its original registration name. This
is recorded because five sibling plans are about to make the same conversion.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **52 files**. Python changed, so the gate ran.

`UV_HTTP_TIMEOUT=600 ./pw verify` → **`=== verify: SUCCESS ===`**, `20275 passed, 14 skipped in
418.05s`, with the quality-gate coverage line reporting all six dimensions clean (mypy production 408
files, ruff, SPDX, plugin-doctor marketplace-wide, mypy test 760 files, whole-tree pytest). Working
tree clean afterwards — no `uv.lock` churn reached a commit.

## Measured deltas (D6)

### Lines — per directory and slice total

`wc -l $(find <dir> -name 'test_*.py')`

| Directory | Before | After | Δ |
|---|---:|---:|---:|
| `manage-config` | 22,648 | 21,795 | −853 |
| `manage-execution-manifest` | 20,069 | 19,584 | −485 |
| `manage-run-config` | 4,113 | 4,113 | 0 |
| `manage-references` | 1,403 | 1,402 | −1 |
| `manage-solution-outline` | 2,595 | 2,594 | −1 |
| `marshall-steward` | 3,788 | 3,788 | 0 |
| **Slice total** | **54,616** | **53,276** | **−1,340 (−2.45%)** |

### Collected test count

`uv run python -m pytest <six dirs> --collect-only -q -o addopts=""`

**2,711 → 2,715 (+4).** The increase is the `_role_of` collapse splitting two multi-assert functions
into one row per step id (+3), plus the token-magnitude round-trip kept as its own named test when the
phase-knob pairs collapsed (+1). **No decrease** — Verification condition 1 holds.

### Coverage

`uv run python -m pytest <six dirs> -o addopts="" --cov=<the six bundle scripts dirs> --cov-report=term`,
run once against `origin/main`'s test tree and once against this branch's, same command, same bundles.

| | Statements | Miss | Branch | BrPart | Total |
|---|---:|---:|---:|---:|---:|
| Before | 7782 | 1297 | 3202 | 403 | **81%** |
| After | 7782 | 1297 | 3202 | 403 | **81%** |

**Byte-identical**, and re-measured against the FINAL tree after the round-1 fix commit, not only
against an intermediate state. Verification condition 2 holds — not merely "same rounded percentage",
the same miss and partial-branch counts.

### plugin-doctor `test-conventions`, per rule

Invocation: the epic README's five-directory `PYTHONPATH` form. Finding rows only; the trailing
`rule,0` summary lines are excluded (counting them inflates every rule by one).

| Rule | Before | After | Δ |
|---|---:|---:|---:|
| `test-docstring-historical-prose` | 24 | **0** | −24 |
| `test-module-preamble-boilerplate` | 137 | 30 | −107 |
| `test-module-line-budget` | 41 | 39 | −2 |
| `subprocess-pythonpath` | 2 | 2 | 0 |
| `test-helper-module-misnamed` | 0 | 0 | 0 |

Per directory after: `manage-config` 17 budget / 7 preamble · `manage-execution-manifest` 13 / 9 ·
`manage-run-config` 3 / 2 · `manage-references` 2 / 0 · `manage-solution-outline` 3 / 4 ·
`marshall-steward` 1 / 8 / 2 `subprocess-pythonpath`.

⚠️ **A correction to this run's own baseline.** The first baseline sweep counted rows matching
`^  test-[a-z-]+,/`, which silently excluded every rule whose id does not start with `test-`. That hid
`subprocess-pythonpath` (2 findings, both in `marshall-steward/test_steward_determine_mode.py`, a file
this diff does not touch — pre-existing, unchanged, and the reason that directory reports
`status: fail`). Both columns above are re-derived with the general `,/home/` row filter, on
`origin/main` and on this branch, so before and after are counted the same way. A rule-name-shaped
filter is exactly the "filtered query believed without a positive control" failure the lane contract
warns about.

### `parse_ns` exception list

**Empty, by non-attempt.** D3 was not started, so no call site was evaluated against `parse_ns` and no
exception was found. This is stated rather than reported as "no exceptions found", because an empty
list from an unrun check tells the operator nothing about whether `parse_ns` needs widening.

### Other ratios

`@pytest.mark.parametrize` decorators 67 → 76. `monkeypatch.setattr` 257 (unchanged),
`@pytest.fixture` 13 (unchanged) — ratio **19.8:1** before and after, untouched because D3 was not
started.

## Verification verdict — the three-part done-when

| # | Condition | Verdict |
|---|---|---|
| 1 | Collected test count does not decrease | **HOLDS** — 2,711 → 2,715 |
| 2 | Coverage does not decrease | **HOLDS** — identical to the statement |
| 3 | Line count drops ≥ 30% of the starting total | **FAILS** — 2.45% against a 30% floor |

**The floor was not reached, and the plan's instruction on that is to report the shortfall rather than
reach it another way.** Shortfall: **15,045 lines** (30% of 54,616 is 16,385; achieved 1,340; target ≤ 38,231).

### Why — the plan's premise for this floor is refuted by measurement

The plan sets this slice the epic's highest floor on the HYPOTHESIS that "its content is the most
tabular — the collapse in D1 is mechanical and its yield is large". Two measurements over the slice
contradict that:

1. **Composition.** Of 54,428 lines across 109 modules: **54.2% code** (29,526), 21.9% blank (11,934),
   14.5% docstring (7,902), 9.3% comment (5,066). Prose totals 23.8%. Deleting *every* comment and
   docstring in the slice — which D5 explicitly must not do — still falls short of 30%.

2. **Actual tabular surface.** An AST scan grouping non-parametrized test functions by body shape
   within each module finds **996** collapsible body lines under exact-shape matching, and **3,996**
   across 113 families under a looser signature (statement-kind sequence + called-name set). That
   looser figure is an **upper bound**: a family only collapses fully where no member carries an extra
   assertion, and each table costs ~10–20 lines of its own. D1's realistic ceiling for this slice is
   roughly **2,500 net lines (4.6%)**, not 16,385.

A defensible total for D1+D3+D4+D5 executed to completion is on the order of **7,000–8,000 lines
(13–15%)**. Reaching 30% would require deleting assertions, which the plan's Out of scope forbids and
which conditions 1 and 2 exist to catch.

**Recommendation to the epic owner:** re-derive this slice's floor from the measured tabular surface
rather than from the tabularity impression, and apply the same re-derivation to `040`–`080` before
they run — five sibling plans are carrying floors set the same way.

## Findings

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | This run | Dropping the bespoke unique `module_name` on `load_script_module` collapses two test modules onto one `sys.modules` entry; the marketplace config modules carry mutable module-level default dicts, so one test's mutation leaks into another's read. 173 order-dependent failures, all green in isolation. | **Fixed** — every converted call preserves its original registration name. Recorded for the five sibling plans about to do the same conversion. |
| 2 | This run | My first D4 sweep pruned `from pathlib import Path` using a `Path(` regex, which misses `Path` used only in **annotations** (`def f(d: Path)`). 38 F821s. | **Fixed** — imports restored from ruff's own F821 report. |
| 3 | This run | The sweep's import-merge regex swallowed trailing `# noqa: I001, E402` comments into the imported-name list, producing `from conftest import I001, load_script_module`. | **Fixed** — noqa codes stripped from name lists. |
| 4 | This run | An import-reordering pass keyed on "first use" matched a mention of `run_script` inside a **module docstring** and moved the import into the docstring body, in two files the D4 sweep never targeted. | **Fixed** — both files reverted; the pass is not re-runnable as written. |
| 5 | `plugin-doctor` | `test-docstring-historical-prose` flags the literal `TASK-001` as a "historical citation" when it names a real fixture artifact (`tasks/TASK-001.json`). Two instances. | **Worked around, not fixed** — the rule lives under `marketplace/bundles/**`, which this plan's Out of scope forbids editing. Both docstrings were reworded to say "one pending task file", which is a genuine improvement (the specific id was incidental to the contract), so the rule now reports zero. **Recorded as a rule defect for the plugin-doctor owner.** |
| 6 | This run | Running the slice while 173 tests were failing left `.plan/marshal.json` modified (66 insertions, 267 deletions) — a test mutates the committed file and only restores it on its success path. | **Recorded, not fixed.** Confirmed collateral of the broken intermediate state, not a standing defect: a clean full-slice run afterwards leaves the file untouched. `.plan/` is outside this plan's surface. The hazard is real — a test that restores state only when it passes turns one failure into a dirty tree. |
| 7 | `manage-config` retired-handler absence test | `conftest.get_script_path` raises `FileNotFoundError` for an absent script, so it cannot express "assert this script is deleted". | **Fixed** — that assertion uses `get_scripts_dir(...) / name` instead. Noted because it is an easy mis-substitution during a D4 sweep. |
| 8 | This run's own report | `doc/` is swept by `test_lane_refactor_cleanup_sweep.py` for retired tokens, and this report named a test file whose **filename** contains one. The build gate went red on my own prose. | **Fixed** — the row names the test by role instead. Worth recording: a run report is inside the scanned tree, so it is subject to the same token guards as the docs it describes, and a filename is enough to trip one. |

### Sub-agent verification findings (round 1)

The verifier confirmed, by row-by-row diff against `git show origin/main:<path>` for all nine tables
then present: **no assertion was dropped in any collapse**; all four Out-of-scope constraints hold
(`git diff --diff-filter=D` empty — no test deleted); removed/added `def test_` counts reconcile
exactly; `ids=` cold-read passes on all three largest tables. It raised 8 defects, all real:

| # | Finding | Disposition |
|---|---|---|
| V1 | The branch-cleanup collapse dropped per-knob present-tense rationale D5 says to KEEP — why 1800 s, what `admin_merge_on_stuck_state` gates, the cross-plan merge-lock. A reader could say what the row pins but not why the value matters. | **Fixed** — restored as row comments in `_BRANCH_CLEANUP_PARAM_DEFAULTS`. |
| V2 | `# D4/D5 new-knob seed assertions — this deliverable (6) …` left heading a section whose three tests had moved into the table. Both orphaned AND the exact deliverable-id prose D5 strips; the doctor rule does not catch it in comments. | **Fixed** — header rewritten. |
| V3 | 16 comments in 15 touched files still described the removed hand-rolled importlib preamble as the current convention; two were dangling directly above a `load_script_module` call. | **Fixed** — all 16 rewritten. Cross-document sweep was already clean (`test/README.md` prescribes `load_script_module`). |
| V4 | Two section headers in `test_effort_read.py` left containing zero tests — the file asserted a partition that no longer existed. | **Fixed** — removed. |
| V5 | `_BRANCH_CLEANUP_ROUND_TRIP = _BRANCH_CLEANUP_PARAM_DEFAULTS[1:4]` encoded the gating "crossed against both accessors" derivation as a slice index: inserting a row silently re-points which knobs get round-trip coverage, with nothing failing. | **Fixed** — the three knobs are named in a frozenset, with a length assertion that fires if one is renamed out of the table. |
| V6 | `TestRoleLoader` collapse weakened three `is None` assertions to `== role`. | **Fixed** — identity restored for the None rows. |
| V7 | A de-historicizing rewrite converted one clause and not the next: "such a comparison silently fails **and the gate steps survived**". | **Fixed** — paragraph rewritten in one tense. |
| V8 | `test_lesson_regression_suggested_fix_two_options` kept the lesson id in its NAME after the comment was rewritten. | **Fixed** — renamed to `test_heading_with_parenthesised_clause_slugifies`. |

The verifier also found D1's done-when 1 unmet in `test_config_defaults.py`: five further
`DEFAULT_PLAN_{EXECUTE,INIT}` / `get_default_config` crossed pairs of the same shape as the
branch-cleanup family, which the first pass missed because the family derivation was run only against
the `phase-6-finalize` prefix. **Fixed** — collapsed into two 5-row tables plus one named round-trip
test. This is a defect in *this run's* derivation, not in the plan's lead: the plan named the
`phase-6-finalize` pair as the exemplar and said to re-derive membership; the re-derivation was scoped
to that exemplar rather than to the whole module.

Its D6 and coverage remarks read a report snapshot still marked `_in progress_`; both are now measured
and recorded above.

## Reviewer participation

_pending PR_

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** not separately instrumented; the dominant measured costs are the six full-slice
  pytest runs (~2m05s each) and one `./pw verify` (6m58s).
- **Population:** this single Claude Code cloud session. ⛔ **Not comparable** to a plan-marshall
  `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under a per-task billing
  boundary this session does not share. No parity figure is offered.

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
