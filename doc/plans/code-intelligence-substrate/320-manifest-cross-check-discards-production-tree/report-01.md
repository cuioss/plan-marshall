# Run report — 320-manifest-cross-check-discards-production-tree (run 01)

**Date (UTC):** 2026-08-17    **Branch:** `claude/manifest-cross-check-production-edn4tw` (harness-assigned)    **PR:** TBD    **Outcome:** completed

## Skills loaded

Loaded by path from the bundle source (`marketplace/bundles/{bundle}/skills/{skill}/SKILL.md`) — the
`plan-marshall` plugin is not installed in this cloud session.

| Skill | Why |
|---|---|
| `.claude/skills/cloud-plan-lane` | The working contract, loaded as the first action |
| `plan-marshall:ref-code-quality` | Always |
| `pm-plugin-development:plugin-script-architecture` | Always |

No skill was unobtainable by both routes.

## Deliverables

### D0 — GATE: the population of private classification lists

**Population found: 2. Components examined: 427** — every `*.py` file under `marketplace/bundles/`
and `.claude/` **as of `origin/main`**, which is the tree the sweep actually ran over. The
same count on HEAD is 428; the extra file is `_footprint_classification.py`, which this change
created and which therefore cannot have been part of the population being derived. Swept along five
independent dimensions so the answer is not one grep's blind spot:

| Dimension | Query |
|---|---|
| A | prefix-tuple constants (`_PREFIXES` declarations) |
| B | predicates naming bookkeeping / implementation / production-ness of a path |
| C | every `bookkeeping` mention in code |
| D | co-located footprint-classifier constants (`_DOCS_SUFFIXES` / `_TEST_DIR_TOKENS`) |
| E | hardcoded `.claude` tree classification |

Dimension D is the decisive one and is independent of the phrasing the others key on: those two
files were the **only** two in the tree carrying that constant pair.

| # | Site | Constant | Consumed by |
|---|---|---|---|
| 1 | `plan-retrospective/scripts/check-manifest-consistency.py` | `_BOOKKEEPING_PREFIXES = ('.plan/', '.claude/')` | `filter_bookkeeping` |
| 2 | `plan-retrospective/scripts/check-routing-decisions.py` | `_BOOKKEEPING_PREFIXES = ('.plan/', '.claude/')` | `_is_bookkeeping` → `footprint_has_production` |

**The originating report named one; the population is two** — the plan's ⛔⛔ confirmed from source.

Examined and **excluded**, each with its reason:

| Candidate | Why it is not in the population |
|---|---|
| `script-shared/scripts/_plan_state_exemption.py` | Covers `.plan/` only — the genuinely-runtime state directory the plan exempts — and already resolves the real question against git trackedness rather than a guess. |
| `script-shared/scripts/workflow/triage_helpers.py::is_test_file` | A test-vs-not classifier *within* the implementation set; declares no tree to be bookkeeping. |
| `manage-config/scripts/_cmd_skill_domains.py::_DEDICATED_PREFIXES` | Skill-*name* prefixes (`recipe-`, `audit-`), not path classification. |
| `marshall-steward/scripts/gitignore_setup.py` | Writes gitignore entries; classifies nothing. |
| `build-npm` / `build-pyproject` route tables | These *are* the oracle's declarations, not private copies of it. |

The population did not grow materially, so the split guard still clears and the sweep was not staged
separately.

### D1 — the oracle lookup, adopted at both sites

**The oracle lookup API did not exist in the shape this plan needs** — the plan's HYPOTHESIS is
refuted, not confirmed. `extension_base._read_build_map_globs` read `build.map` but **projected the
`role` away**, returning globs only. Added, beside it:

- `read_build_map_routes()` — the single `build.map` reader, returning `(glob, role)` pairs.
  `_read_build_map_globs` is now *derived* from it, so the build-decision activation gate and the
  role lookup cannot read a different build map.
- `resolve_route_role(path, routes)` — the per-path lookup, matching through the existing public
  `route_matches`. Precedence is `production` ▸ `test` ▸ `config`, applied over the matched set
  rather than by first match, so the answer is **order-independent** (it cannot depend on which
  domain the seed wrote first) and **implementation-favouring** (a contested path is retained, which
  can only widen what a rule examines).

Both consumers now share **one** module — `plan-retrospective/scripts/_footprint_classification.py`
— so the population going forward is 1, not 2. Verified per site:

| Site | Assertion |
|---|---|
| `check-manifest-consistency` | `TestProjectLocalTreeSurvivesFilter::test_multi_file_project_local_footprint_is_not_filtered` |
| `check-routing-decisions` | `TestProjectLocalTreeSurvivesFilter::test_routing_check_sees_project_local_production` |

**The plan's LOAD-BEARING claim was READ, not assumed.** `build-pyproject/scripts/extension.py::_project_local_skill_globs()`
emits `('{root}/*.py', 'production')` for every root `marketplace_paths.get_project_skill_roots()`
returns — `('.claude/skills',)` on the Claude target. The build map routes `.claude/skills/*.py` as
**production** while both checks declared the whole `.claude/` tree bookkeeping. Contradiction
confirmed from source.

**Reproduced in the clone, as the plan asked.** A 7-path footprint of this project's own
project-local production modules through the pre-fix manifest check:
`files_total: 7, files_filtered: 6, files_kept: 1` — 6 of 7 discarded, the same shape as the
originating report's 10-of-11, with `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`
(9,470 lines) among the discarded. Post-fix the same input yields `files_filtered: 0, files_kept: 7`.

#### One stated divergence from the plan's D1 sentence

The plan says *"only config or unclassified paths are bookkeeping."* Config is dropped as written.
**`unclassified` is RETAINED**, and that is a deliberate divergence:

- The build_map role vocabulary **deliberately has no `documentation` role** (documentation has no
  build-system owner — `_extension_constants.py` says so explicitly), so *every* `.md`/`.adoc` path
  is unclassified. Dropping unclassified would drop all documentation before rule M1, leaving M1's
  own `is_docs_path` predicate unable to ever return `True` in its culprit comprehension — a
  detector that cannot detect, which is precisely the archetype this plan exists to remove, newly
  created by its own fix.
- It would equally drop every unrouted-but-real path (`.github/workflows/*.yml`, `.gitignore`,
  shell scripts), opening a fresh blind spot in M1/M2/M3.

Retaining is strictly fail-closed: it can only widen what a rule examines, never narrow it. The
observable cost is that a `.claude/` path the build map does *not* route (e.g.
`.claude/settings.local.json`) is no longer blanket-dropped; that is pinned by
`test_unrouted_dotfile_path_is_retained_not_assumed_bookkeeping`, and it is the same correction that
stops `audit.py` being dropped. The reduction is never silent — D2 reports it.

### D2 — a reduced input set reports the reduction

`apply_input_reduction` runs after every evaluator, so no rule can forget either obligation:

- every diff-fed check that ran against a reduced input set carries the reduction in its message
  (`manifest_version_recognized` is exempt — it reads the manifest body alone);
- a check that would otherwise emit a bare clean `pass` while `files_filtered > files_kept` takes the
  new status **`indeterminate`**, message prefixed `VERDICT WITHHELD`.

A `fail` is never downgraded, and the reason differs by rule shape — round 2 found the blanket
version of this sentence false and it is not repeated here. For the rules that fail on a culprit
**present** in the survivors (M1/M2/M3), a culprit that survived is real and filtering can only have
concealed others. For M4, the one rule that fails on the survivors being **empty**, that argument
does not apply at all, because the filter is what empties the set; its verdict rests instead on every
drop category being a *positive* classification. A `skip` is never downgraded either: the rule did
not apply, which filtering did not decide. The `diff` block now
publishes `filtered_by_category` (one count per category, **always present even at zero**),
`oracle_available`, and `majority_discarded`; `summary` gains `indeterminate`.

Verified adversarially by `test_majority_filtered_footprint_never_yields_a_bare_pass` (5-of-6
discarded ⇒ `indeterminate`), with `test_unreduced_footprint_still_passes_cleanly` as the negative
control.

### D3 — the unreachable rule

**It is M3 (`evaluate_tests_only`), not M4.** M4 compares `phase_6.steps` against a bare
`branch-cleanup`, and `DEFAULT_PHASE_6_STEPS` *is* bare — M4 fires, confirmed by running it.

M3 compared `phase_5.verification_steps != ['module-tests']`. The composer's
`DEFAULT_PHASE_5_STEPS = ('verify:quality-gate', 'verify:module-tests')`, and its boundary
normalization (`manage-execution-manifest.py`, `phase_5_candidates = [canonicalize_step_key(s) …]`)
strips only `default:` — never `verify:`. `_role_of`'s docstring states the invariant outright:
*"Every built-in verify step is a parameterized canonical-verify step (`default:verify:{canonical}`
or the bare `verify:{canonical}` form)."* So `verification_steps` reads `['verify:module-tests']` and
the bare comparison **can never be true on a composer-produced manifest**.

Fixed by `normalize_verification_step`, which strips `default:` via the shared
`canonicalize_step_key` and then the `verify:` prefix. The bare form is still accepted — archived
manifests carry it (`test_m3_still_recognises_the_bare_module_tests_form`).

⛔ **The pre-fix test suite could not catch this**: `test_plan_retrospective_manifest.py`'s fixtures
hardcoded the bare `['module-tests']` / `['quality-gate', 'module-tests']` forms, driving M3 with a
shape production never produces. Both fixtures were corrected to the composer's real shape, and the
suite still passes — so no test was passing *only* because of the retired form.

### D4 — a supplied-but-unresolvable path

Root cause confirmed at `check-routing-decisions.load_diff_files`: `if not path.exists(): return []`
— the same value an **absent** `--diff-file` returns. `cmd_run` then fell through to
`resolve_footprint`, and an unresolvable footprint degrades the mis-prune checks to `skip`.

The asymmetry the plan names is real and was verified in source: the sibling
`collect-fragments add --fragment-file` resolves a relative path against the plan directory
(`_resolve_fragment_path`, `collect-fragments.py:128-131`), while the documented capture pattern
`--diff-file work/footprint.txt` (SKILL.md, Aspect 13) did not.

Fixed with **both** halves of the plan's option: shared `_footprint_resolver.resolve_diff_file_path`
resolves a relative argument plan-directory-first, cwd-second, **and raises** when no candidate
exists, naming every candidate tried. Adopted by both scripts, so the documentation and the scripts
now agree. Verified by equality:
`test_documented_relative_form_matches_the_absolute_form` asserts the two invocations produce the
**same** `mis_prune_checks`.

#### Declared collateral

Two changes that are neither a deliverable nor a defect fix, declared rather than left for a reader
to notice:

- **`manifest-crosscheck.md`'s M1 skip-message example was corrected** to `'… non-empty or
  early_terminate=true'`. `origin/main`'s code already emitted that string, so this repairs a
  pre-existing doc/code mismatch found while updating the surrounding block.
- **An existing test's expected verdict changed.** `test_pass_when_only_bookkeeping_changes` lost
  `.claude/settings.local.json` from its input (that path is no longer blanket-dropped) and its
  expected M2 verdict moved `pass` → `indeterminate` (every remaining supplied path is filtered, so
  D2 withholds the verdict). Both mechanisms are the deliverables working as intended, but the fact
  that a pre-existing test's expected verdict moved is stated here explicitly.

### D5 — tests, each verified to FAIL pre-fix

`test/plan-marshall/plan-retrospective/test_footprint_oracle_classification.py` carries **18 test
functions, collecting as 18 cases**, and `test/plan-marshall/script-shared/test_extension_base.py`
gains **11 test functions, collecting as 13 cases** (two are parametrized). Both figures re-derived
at the moment of this claim; a count of test *functions* and a count of *collected cases* are
different numbers and both are stated.

**The red-first run covered the 11 tests that existed at that point** — the file then held 11 test
functions, and the recorded result is **10 failed, 1 passed**. The single pass was
`test_m3_still_recognises_the_bare_module_tests_form`, which pins pre-existing back-compat behaviour
and is a regression pin rather than a red-first test — stated rather than counted as coverage.

The remaining 7 tests were added later and so have **no red-first record**; each was instead shown
non-vacuous by mutation (below). Naming which is more useful than counting them:
`test_unclassifiable_path_counts_as_production_for_the_mis_prune` and
`test_documentation_alone_does_not_count_as_production` (fail-closed pins, added in round 1), and the
five added in round 2 to close that round's findings —
`TestTestRecognitionSurvivesAnOracleWithNoTestRoute` (three),
`TestBranchCleanupRuleDoesNotClaimAnEmptyDiff` (one), and
`TestConsumerDispatchSetsAreKnownCategories` (one).

| Deliverable | Test | Pre-fix |
|---|---|---|
| D5a | `test_multi_file_project_local_footprint_is_not_filtered` | FAIL (`files_filtered` 5, expected 0) |
| D5a | `test_runtime_state_directory_is_still_bookkeeping` | FAIL |
| D5a | `test_routing_check_sees_project_local_production` | FAIL (`pass`, expected `fail`) |
| D5b | `test_majority_filtered_footprint_never_yields_a_bare_pass` | FAIL (bare `pass`) |
| D5b | `test_unreduced_footprint_still_passes_cleanly` | FAIL (no `indeterminate` key) |
| D5c | `test_m3_fires_on_canonical_verify_step_shape` | FAIL (`skip`, expected `fail`) |
| D5c | `test_m3_passes_when_the_diff_really_is_tests_only` | FAIL (`skip`, expected `pass`) |
| D5d | `test_documented_relative_form_matches_the_absolute_form` | FAIL |
| D5d | `test_unresolvable_diff_file_fails_loudly` | FAIL (succeeded, reporting skip) |
| D5d | `test_manifest_check_also_resolves_the_relative_form` | FAIL |

#### Mutation campaign — every new guard shown non-vacuous

Each guard was re-run against the specific defect it names, not a neighbouring one:

| Mutation | Guard that caught it |
|---|---|
| `resolve_route_role` precedence → first-match | `test_production_wins_over_config_in_either_declaration_order`, `test_test_wins_over_config_in_either_declaration_order` (the adverse-order parametrization only) |
| `_DROPPED_CATEGORIES` gains `unclassified` (the plan-literal reading) | `test_unrouted_dotfile_path_is_retained_not_assumed_bookkeeping` |
| `_PRODUCTION_CATEGORIES` loses `unclassified` | `test_unclassifiable_path_counts_as_production_for_the_mis_prune` |
| D2 downgrade disabled | `test_majority_filtered_footprint_never_yields_a_bare_pass` |
| M3 normalization removed | `test_m3_fires_on_canonical_verify_step_shape` |
| Test-convention rung removed from `classify_path` (the B1 defect) | `test_tests_only_footprint_is_not_a_mis_prune`, `test_both_checks_agree_on_test_ness` |
| M4's `"diff is empty"` message restored (the B2 defect) | `test_fully_filtered_footprint_names_the_reduction_not_an_empty_diff` |
| A dispatch set pointed at a non-existent category | `test_dispatch_sets_are_subsets_of_the_category_vocabulary` |

Every mutation was caught by the guard that names it; each was reverted and the tree restored
(`git diff --stat`) before proceeding. The first five were run in round 1, the last three in round 2
against the guards that round added.

Two details worth recording rather than smoothing over. The precedence mutation was caught by only
**one** arm of each parametrized pair — the adverse declaration order — which is the arm that exists
for exactly that reason; the other order agrees with first-match by construction. And removing the
test-convention rung failed two guards rather than one, which is what a shared classifier should do:
the consumer-level test and the classifier-level test see the same defect from different ends.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** — production scripts and tests
changed — so the full `./pw verify` ran, over the whole branch diff, from the repository root.

**Result: `=== verify: SUCCESS ===`.** Read from the tool output, not the exit code: **20687 passed,
14 skipped** (20701 collected), and the run's own coverage line reports **COMPLETE over all six
dimensions** — mypy(production) [413 files], ruff [`marketplace/bundles`, `test`, `.claude`], SPDX
headers, plugin-doctor [marketplace-wide], mypy(test) [766 files], and module-tests [whole-tree
pytest].

⚠ **These figures are the DELIVERED tree's, re-measured after the last code change.** An earlier
draft of this section carried an earlier commit's figures, which round 2 caught: the run had been
recorded by the same commit that then changed three production files, so the number described a tree
that was no longer the one being shipped. A build-gate figure is only evidence about the tree it ran
against, and it is re-derived here rather than carried forward.

`UV_HTTP_TIMEOUT=600` was exported, per the lane contract's note about the wrapper's dependency
fetches; no `uv` HTTP timeout occurred. The build left no `uv.lock` churn — `git status` was checked
before staging, and every commit stages named paths rather than `git add -A`.

## Findings

Recorded **per instance**. Sources: the pre-PR verification sub-agent (rounds 1–3), the build gate,
and PR review (below).

### Round 1 — 2 behavioural, 12 false statements

Both behavioural findings were confirmed by RUNNING the code, not by reading it.

| # | Source | Finding | Disposition |
|---|---|---|---|
| B1 | round 1 | Moving test-ness onto the oracle lost it wherever the oracle is silent: with no `test` route, a tests-only footprint drove `mis_prune` to `fail` | **fixed** — test recognition by convention restored in the shared classifier |
| B2 | round 1 | Rule M4 emitted `"diff is empty"` over a 2-path diff the filter had emptied, and `apply_input_reduction` declined to downgrade it | **fixed** — message states what is true; the rationale now distinguishes the two rule shapes |
| A1 | round 1 | "a reduced input can only have hidden more violations" — true of M1/M2/M3, false of M4 (2 sites) | **fixed** at both |
| A2 | round 1 | Docs recognition described as the change-footprint classifier's set; it is not (3 sites) | **fixed** at 2 of 3 in round 1; round 2 found the third (see F6) |
| A3 | round 1 | "preserves the pre-oracle behaviour for unrouted paths" — false for test paths | **fixed** |
| A4 | round 1 | Oracle-unavailable note: "only runtime-state paths were classifiable" | **fixed** (round 2 found the replacement also false — see F3) |
| A5 | round 1 | Report said "6 oracle-API tests"; the diff adds 11 functions / 13 collected | **fixed**, both units stated |
| A6 | round 1 | Red-first totals (10 failed, 1 passed = 11) did not cover the file's 13 tests | **fixed** — the red-first population is now stated as the 11 that existed then |
| A7 | round 1 | Build-gate section promised a record it did not contain | **fixed** (round 2 found the recorded figures stale — see F8) |
| A8 | round 1 | `CATEGORIES` comment claimed consumers quantify over it; both dispatches are name lists | **fixed**, plus a subset guard |
| A9 | round 1 | "no declared route covers it at all" used as a synonym for `unclassified` (2 sites) | **fixed** at both |
| A10 | round 1 | "the two cannot disagree about the same path" — too strong | **fixed** |
| A11 | round 1 | "never as a bare `{canonical}`" — the `--phase-5-steps` CSV fallback forwards its argument verbatim (4 sites) | **fixed** at all 4 |
| A12 | round 1 | `manage-execution-manifest/SKILL.md`'s worked example: `verification_steps` and `step_execution_tier` could not both describe one manifest | **fixed** |
| C1 | round 1 | Manifest-side D4 equality test asserted one count, not the verdict | **fixed** — compares `checks`/`findings`/`summary`/`diff` |
| C2 | round 1 | D0 reported the count found but no number examined | **fixed** (round 2 found the number named the wrong tree — see F13) |
| C3 | round 1 | Summary buckets hardcoded where the sibling derives them | **fixed** (round 2 found the replacement inverted the sibling's rule — see F4) |
| C4 | round 1 | Undeclared collateral: an M1 skip-message doc fix | **declared** |
| C5 | round 1 | Undeclared test-meaning change | **declared** |
| C6 | round 1 | This repo's incident narrative in a shipped bundle module | **fixed** at 1 of 4 in round 1; round 2 found the rest (see F11) |

### Round 2 — 1 behavioural, 12 false statements

⭐ **Round 2's most valuable finding, F12, was a behavioural regression round 1's own fix
introduced — and which round 1's prose actively denied.** Unifying the two docs predicates gave the
routing consumer the manifest consumer's `/references/` and `/templates/` directory tokens, which it
never had (`origin/main`'s `_is_docs` was `endswith` only). An unrouted `src/references/helper.py`
therefore moved from *production* to *documentation*, turning a `mis_prune` `fail` into a `pass` —
**the exonerating direction**, which is precisely what the `unclassified` handling exists to refuse.
The docstring beside it asserted the sets were "carried over unchanged".

| # | Source | Finding | Disposition |
|---|---|---|---|
| F12 | round 2 | Docs directory tokens widened the routing consumer's recognition toward exoneration, denied by the docstring | **fixed** — classification uses a suffix-only predicate (`is_docs_suffix_path`); the wider `is_docs_path` stays the manifest rules' own predicate, where it cannot decide what is dropped |
| F1 | round 2 | `TEST_DIR_TOKENS` claimed to be the UNION of both retired sets; it is not — the routing copy's unanchored tokens also matched `latest/`, `contest/`, `mytest/` | **fixed** — states what the set is, names the substring defect deliberately dropped, and names the direction (fail-closed) |
| F2 | round 2 | "Both consumers share it, so they cannot disagree" — they reach test-ness by different paths and do disagree | **fixed**; the mis-named guard renamed and split into three that test what they say |
| F3 | round 2 | The rewritten oracle-unavailable note was falsified by the same commit's own B1 fix — the convention rung assigns `test` (= `ROLE_TEST`) with no oracle | **fixed** |
| F4 | round 2 | `_STATUS_BUCKETS` claimed to mirror the sibling's shape while inverting it: `.get(status)` DROPS an unmapped status, reproducing the absent-reads-as-nothing defect the sibling's docstring forbids | **fixed** — `.get(status, status)`, so `sum(values) == len(checks)` unconditionally |
| F5 | round 2 | "Three things, and only three" — there are four non-oracle rungs; `report` was omitted, and "every OTHER classification comes from the oracle" was false for it | **fixed** — the rungs are named, not counted |
| F6 | round 2 | A2 closed at 2 of 3 sites, the survivor being the exact phrasing the ⛔ block ten lines above forbids | **fixed** |
| F7 | round 2 | A1 closed at 2 of 3 sites; the run report still stated the retracted blanket rationale | **fixed** |
| F8 | round 2 | The recorded build-gate figures predated the commit recording them (20675 vs HEAD's collection) | **fixed** — re-run on the delivered tree; see Build gate |
| F9 | round 2 | `test_pass_when_only_bookkeeping_changes` asserted `indeterminate` | **fixed** — renamed |
| F10 | round 2 | M4's "so there is nothing to push/clean" is false for `report` and `config`; only `runtime_state` is git-ignored | **fixed** — the finding states what it knows and stops |
| F11 | round 2 | The C6 remedy landed at 1 of 4 shipped sites | **fixed** at all 4, in one uniform verifiable form |
| F13 | round 2 | D0's denominator (428) counted HEAD, including the file the fix created; the sweep ran over `origin/main`'s 427 | **fixed** — re-derived via `git ls-tree -r origin/main` |

### Round 3 — see the stop record below

## Reviewer participation

## Cost

## Contract check (Step 9)

## What have we learned (Step 9)

## Residue
