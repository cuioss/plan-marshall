# Verification — 160-build-gate-coverage-parity

**Verified against:** commit `ac06e4fc94782328f87d1395472a72b7e7a8559d`   **Landed as:** PR #1174, commit `819349fe704b51eb252e6a163b88c47e1edf9437`   **Verdict:** implemented-with-gaps

## Method

Ground truth was taken from the tree at HEAD, with `report-01.md` treated as the claim under test.

**Files opened and read in full or in the relevant span:** `plan.md`; `report-01.md`; `build.py`
(imports, `_FRESHNESS_SUSPECT_RC`, `_mypy_collect_count`, `_run_mypy`, `_skip_empty_mypy_scope`,
`cmd_compile`, `cmd_test_compile`, `cmd_quality_gate`, `cmd_verify`, `main`);
`marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py` (whole file);
`marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_test_scope_divergence.py`
(`_module_for_path`, `resolve_test_scope`);
`marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`
(§ "Coverage parity with CI…", the module-tests branch list, the Mark-Step-Complete detail variants,
§ "Adjacent item deliberately not covered");
`marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/external-step-contract.md`
(the `display_detail` ≤80-character constraint);
`marketplace/bundles/plan-marshall/skills/ref-code-quality/standards/error-handling.md`
(rule headings (b) and (d), to confirm the cross-link the module docstring asserts);
`marketplace/bundles/plan-marshall/skills/build-pyproject/standards/pyproject-impl.md`
(§ "Verification-Target Trust"); `pyproject.toml` (`[tool.ruff.lint]`, `[tool.mypy]`);
`.github/workflows/python-verify.yml`; `.github/project.yml`;
`test/plan-marshall/build-pyproject/test_gate_coverage.py`; `test/default/test_build_verify.py`;
`test/plan-marshall/build-pyproject/test_test_scope_divergence.py`.

**Diffs read:** `git show --stat -M 819349fe`, `git show 819349fe -- build.py`, `… -- test/default/test_build_verify.py`,
`… -- marketplace/…/pre-push-quality-gate.md`, `… -- test/plan-marshall/build-pyproject/test_pyproject_build.py test/marketplace/test_spdx_enforcement.py`,
plus `git show 819349fe^:build.py` / `819349fe^:pyproject.toml` to check the report's line citations against
the tree they were made from.

**Tests run.**

- `uv run python -m pytest test/plan-marshall/build-pyproject/test_gate_coverage.py -o addopts="" -q` → **22 passed** (11 at
  landing, 11 more added later by PR #1239).
- `uv run python -m pytest test/default/test_build_verify.py -o addopts="" -q` → **25 passed**.

**Functions executed** (not read) via `uv run python -c …` against the real module:

- `classify_check_duration(660, 2.0)` → `plausible=True`; `(660, 5.0)` → `True`; `(660, 0.33)` → `True`;
  `(660, 0.0)` → `False`; `(100, 0.0)` → `False`; `(99, 0.0)` → `True`.
- `parity_population()` → 9 cells.
- `render_coverage_summary(…)` for a module-scoped boundary — reproduced the COMPLETE text verbatim.
- `build._mypy_collect_count(['marketplace/bundles'])` → 408; `+ '.claude'` → 414; `['test']` → 772.

**Mutation applied.** Saved `build.py` bytes to the scratchpad, rewrote `build.py:306` from
`['uv', 'run', 'mypy', '--no-incremental', *paths]` to `['uv', 'run', 'mypy', *paths]`, re-ran
`test/default/test_build_verify.py` → **4 failed** (`test_compile_runs_mypy_cold_with_no_incremental` plus the
three updated argv assertions), restored the file from the saved copy. `git status --porcelain` is clean apart
from this file and `gaps.md`.

**GitHub state checked** for PR #1174 via the GitHub MCP server: `get` (merged 2026-08-11T22:28:27Z by
`cuioss-oliver`, head `claude/gate-coverage-parity-wra7b0`, 9 files, +1054/-23), `get_comments` (2),
`get_reviews` (1), `get_review_comments` (0 threads).

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1 | Derive the parity population before fixing any instance | Table exists, derived from configuration, population stated | yes | yes | yes | **no** | `report-01.md` § D1 table (9 rows, both axes, population stated NON-EMPTY); citations re-checked against `819349fe^` — `pyproject.toml:238` = `select`, `build.py:244-252` = `cmd_compile`, `:340-342` = ruff paths, `:349-352` = SPDX paths — all accurate. Missing rows: `build.py` itself and `marketplace/targets/**` are ruff- and mypy-invisible on **both** sides (`build.py:463`, `build.py:339-357`, `build.py:475`) — see G5 |
| D2 | Linter and type-check parity | Local rule set and file set both match CI's | n/a (no change) | yes | yes | yes | Single shared config confirmed: `pyproject.toml` `[tool.ruff.lint] select = ["E","W","F","I","B","C4","UP"]` (no `RUF`) and one `[tool.mypy]`; `.github/workflows/python-verify.yml` delegates to the reusable workflow with no goal override and `.github/project.yml` sets no `pyprojectx-verify-goals`; `build.py:632` `verify` chains `quality-gate → test-compile → module-tests` |
| D3 | Divergence-gate branch integrity | No branch can report clean without stating what it examined | n/a (no change) | yes | yes | **no** | `_test_scope_divergence.py:255` `divergence_possible = len(scoped_modules) > 1 or shared_infra_touched or bool(unresolved_paths)`; branch 5 hard-ordered before branch 6 (`pre-push-quality-gate.md:292`); `marketplace/targets/**` → `_module_for_path` returns None → `unresolved_paths` → whole tree. The file is untouched by `819349fe` (dedup constraint honoured). Gap: the module-tests `whole_tree_available == false` honest-degradation branch still lands on Branch A's "module-tests green" detail — see G4 |
| D4 | Freshness: an implausibly fast gate is a failure signal | Stale cache can no longer produce a clean verdict; implausible duration surfaced | yes | yes | **partly** | **no** | Cold run: `build.py:306` is the tree's only project mypy invocation and always carries `--no-incremental`; mutation of that line turns 4 tests red. Duration check: `_gate_coverage.py:86` `MAX_ANALYSIS_THROUGHPUT = 2000.0` — executed `classify_check_duration(660, 2.0)` and `(660, 5.0)` → **plausible=True**, i.e. the plan's own motivating incident is not flagged — see G1 |
| D5 | The gate reports what it did NOT check | A partially-checked footprint produces a distinguishable verdict | yes | yes | yes | **no** | `CoverageBoundary` (`_gate_coverage.py:160`), `render_coverage_summary` (`:362`), threaded through `cmd_quality_gate` (`build.py:423`) and `cmd_verify` (`build.py:539`); `pre-push-quality-gate.md:50-73` + the DEGRADED `--display-detail` variant at `:355-370` (61 chars before `{N}` expands, inside the ≤80 ceiling in `external-step-contract.md:52`). Gaps: the only production caller of `record_degraded` is the freshness path (`build.py:317`); a `_skip_empty_mypy_scope` skip records nothing (G8); the module-tests degradation branch got no variant (G4) |
| D6 | Tests, each verified to FAIL pre-fix | All hold and the report states each was seen red first | yes | yes | yes | **no** | 11 tests in `test_gate_coverage.py` at `819349fe` (re-counted: `git show 819349fe:… | grep -c '^def test_'` → 11), 5 new + 3 updated in `test_build_verify.py`; both files green today (22 / 25). Red-first re-confirmed for 4 of the 8 by mutation. `test_parity_population_is_non_empty` asserts a hand-written 9-tuple is non-empty — see G2 |

**D1.** The table itself is sound and its citations check out against the pre-change tree. What it does not
enumerate is the pair of dimensions where *both* sides are blind: `build.py` — the file this plan modifies —
is passed to neither `ruff check` (`build.py:463`: `[BUNDLES_DIR, TEST_DIR, CLAUDE_DIR]`) nor mypy
(`build.py:339-357`: `[BUNDLES_DIR]` plus `.claude` when collectable); it reaches only the SPDX sweep
(`build.py:475`). `marketplace/targets/**` is in the same position, and the report discloses that one in a
parenthetical under sampled hole 4 but carries neither into § Residue. D1's mandate was to derive the
population rather than adjudicate the sample, so a shared-blind cell belongs in the table with an explicit
"equal, and equal to zero" verdict.

**D4.** `--no-incremental` is real, unconditional and load-bearing — the mutation confirms the tests hold it
down. The second half of the done-when is where it falls short. The plan's problem statement records the
incident as "the local test-compile gate **passed in 2–5 seconds**" over "660 files"; that is 132–330 files/s,
and the implemented ceiling is 2000 files/s, so `classify_check_duration` returns `plausible=True` for it. The
only test asserting the positive direction (`test_large_scope_reported_in_near_zero_time_is_flagged`) uses
660 files / 0.05 s = 13 200 files/s — 40× beyond the observed case. The negative direction is genuinely safe
and was verified. See G1.

**D5.** The property is implemented and the wording is good — I re-rendered the PARTIAL text and it does say
"this pass does NOT certify the whole tree" and "A clean exit here is NOT a full pass". The incompleteness is
in the *set of conditions that can make a verdict PARTIAL*: grepping `record_degraded` across the tree finds
exactly one production caller (`build.py:317`, the freshness backstop). Every other way the gate can check
less than its nominal scope — the `_skip_empty_mypy_scope` early return at `build.py:344` and `build.py:364`,
the module-scoped run that never invokes plugin-doctor — leaves the boundary in its `complete` state.
PR #1239 later added a derived "not run in this gate at all" line that partially covers the second case; see G6
for the inaccuracy that line introduces on a module-scoped run.

**D6.** The tests exist, are collected, and pass. The red-first claim is re-confirmable only for the four
assertions that key on `--no-incremental`; the remaining four (the two `quality-gate` freshness tests and the
two `verify` coverage-summary tests) exercise symbols that did not exist before the change, so "red first"
there means "collection/attribute error", which is what the report says. `test_parity_population_is_non_empty`
is the weakest of the set — see G2.

## Report accuracy

Re-derived and **confirmed**:

- The five sampled holes' dispositions. RUF absent from the single shared `select` — confirmed by reading
  `pyproject.toml` (`select = ["E", "W", "F", "I", "B", "C4", "UP"]`) and by there being no second ruff config.
  `test-compile` unconditional in `cmd_verify` — confirmed at `build.py:559`. Empty-vs-unresolved distinguished —
  confirmed at `_test_scope_divergence.py:255` and by `test_resolve_test_scope_empty_footprint` /
  `test_empty_registered_module_set_resolves_nothing`. `marketplace/targets` SPDX-covered by the unconditional
  whole-tree arm — confirmed at `build.py:475` and `pre-push-quality-gate.md:224`.
- The dedup constraint: `_test_scope_divergence.py` and its test file are absent from `git show --stat -M 819349fe`.
- The deferral rationale the Residue section leans on: `pre-push-quality-gate.md:252` § "Adjacent item
  deliberately not covered" exists and says what the report says it says.
- The fail-closed cross-link: `ref-code-quality/standards/error-handling.md:289` is "(b) Fail closed on
  undetermined, `None`, or empty state" and `:347` is "(d) Require an affirmative success signal, never
  absence-of-change" — the two rules `_gate_coverage.py` names.
- The counts: 11 tests in `test_gate_coverage.py` at landing; 5 new + 3 updated in `test_build_verify.py`;
  9 files / +1054 / −23 in the PR.
- Reviewer participation: `coderabbitai[bot]` and `cuioss-review-bot[bot]` issue comments, `sourcery-ai[bot]`
  a COMMENTED review carrying exactly the quoted weekly-rate-limit text, 0 inline review threads. 1-of-3 is right.
- The quoted gate output format. At `819349fe`, `render_coverage_summary` emitted
  `>>> coverage: COMPLETE — checked over full scope: …`, matching the report's quotation. (HEAD's wording differs
  because PR #1239 extended it.)
- The file counts are consistent with tree growth: the report's 393 production / 708 test files against today's
  414 / 772 from `_mypy_collect_count`.

**Contradictions and imprecisions found:**

1. **"derived, not hand-listed" is not true of the code.** The report says the population is "Derived from the
   tool configuration on both sides", and `pre-push-quality-gate.md:71` states the population is "**derived, not
   hand-listed** (`_gate_coverage.parity_population`)". `parity_population()` (`_gate_coverage.py:434-457`) is a
   literal 9-tuple; nothing in it is computed from `pyproject.toml`, `build.py` or the workflow at run time, and
   the function has no production consumer (grep for `parity_population` finds only the module itself, the doc
   sentence, and the tests). The *analysis* was derived; the *artifact* is a transcription. See G2.
2. **The coderabbit quote drifted.** The report records "Next review available in 41 minutes"; the stored
   comment body (last edited 2026-08-11T22:00:45Z) reads 30 minutes. The comment is bot-mutable, so this is a
   snapshot difference rather than a fabrication — noted for completeness, not raised as a gap.
3. **A duplicate `## Cost` section** appears in `report-01.md`, the second one with the body `_pending_`,
   directly after the completed one. See G7.
4. **Contract-check step 3 reads as if the plan directory pre-existed** ("present on arrival; no repair
   needed"). The landed diff contains `R100 doc/plans/truthful-signals/160-build-gate-coverage-parity.md →
   doc/plans/truthful-signals/160-build-gate-coverage-parity/plan.md`, so the directory step *was* performed in
   this commit. The parenthetical most plausibly scopes to the first-instruction block rather than to the
   directory, so this is ambiguity, not a false claim.

## Out-of-scope compliance

- **"Changing what CI checks"** — respected in substance. No rule, path set or workflow was widened. One
  nuance the report does not name: CI runs the same `build.py`, so CI's mypy invocations now also carry
  `--no-incremental` and CI can now exit `3` on a freshness-suspect verdict. CI had no restored `.mypy_cache`
  to begin with, so the checking behaviour is unchanged, and the direction of any change is toward strictness,
  never away from it. The boundary's intent ("never loosen CI to match a weaker local gate") is honoured.
- **Lesson-residue promotion** — not attempted. Nothing under `.plan/` is touched; the tree confirms no
  lessons-store artifacts in the diff.
- **The review-side half** — not re-absorbed. No `automatic-review` or review-apparatus file appears in the diff.
- **Undeclared collateral** — none. All nine files in `git show --stat -M 819349fe` are accounted for: `build.py`
  and `_gate_coverage.py` (D4/D5), `pre-push-quality-gate.md` (D5), two test files added/extended (D6), the plan
  directory rename plus `report-01.md` (lane contract), and `test_spdx_enforcement.py` / `test_pyproject_build.py`
  disclosed in § Findings as co-evolution of stubs that the new `boundary` kwarg and the freshness clock broke.
  The co-evolution edits are stub-signature and clock-patch changes only — confirmed by reading that diff.

## Residue carried forward

| Item as declared in report-01.md | Status in today's tree |
|---|---|
| `build.py` `verify` subparser `help='Full verification (quality-gate + module-tests)'` omits `test-compile` | **Still open.** `build.py:632` is unchanged, and `cmd_verify` still chains `test-compile`. The recorded deferral it defers to is real (`pre-push-quality-gate.md:252`) |
| `pyproject.toml` `[tool.mypy]` comment "`./pw verify` never mypy-checks `test/`" is loosely worded | **Still open.** The comment is verbatim in `pyproject.toml`'s `[tool.mypy]` block above `exclude = [...]` |
| The pytest module-scope conditional subset (reverse cross-module coupling) is the sibling plan's territory | **Still open.** `_test_scope_divergence.py:255` is unchanged since PR #1082 (predating this plan); no later commit touches the file |

## What could NOT be verified

- **The CI half of the parity derivation.** `.github/workflows/python-verify.yml` pins
  `cuioss/cuioss-organization/.github/workflows/reusable-pyprojectx-verify.yml@…v0.19.0`. That repository is
  not reachable from this session (the GitHub MCP server refuses it: "repository … is not configured for this
  session"), so the report's claims that the reusable workflow runs `./pw <verify-goals>` with `verify` as the
  default, and that it restores only the uv package cache and never `.mypy_cache`, are **taken on the report's
  word**. Everything downstream of "CI runs `./pw verify` from this repository's `pyproject.toml`" is verified;
  the premise itself is not.
- **"Three mypy errors reached `verify` as a direct result"** and **"CI checked 660 files and found 2 real type
  errors"** — the plan itself labels both as REPORTED-not-re-derived, and neither is recoverable from this clone.
  They are used here only as the calibration target in G1, where the *stated* numbers are what matter.
- **`./pw verify` → "19060 passed, 14 skipped (304s)"** — not re-run (a full verify is a ~5-minute build and the
  tree has advanced by ~120 commits since). The two test files this plan added or changed were run individually
  and are green.
- **The D5 cold-read and the Step-6 verification sub-agent** — both are transcript-only events. Their *outputs*
  (the PARTIAL wording, the diff) are verified; the fact that an independent agent was shown them is not
  checkable from the tree.
- **Whether the eight red-first failures were literal assertion failures rather than collection errors** — four
  are re-confirmable by mutation (done); the other four test symbols that did not exist pre-change.
