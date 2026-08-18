# Run report — 320-manifest-cross-check-discards-production-tree (run 01)

**Date (UTC):** 2026-08-17 – 2026-08-18    **Branch:** `claude/manifest-cross-check-production-edn4tw` (harness-assigned)    **PR:** [#1288](https://github.com/cuioss/plan-marshall/pull/1288)    **Outcome:** completed

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

**Reproduced in the clone, as the plan asked.** A 7-path footprint — this project's six
project-local production modules under `.claude/skills/`, plus one `marketplace/bundles/` source file
as a control — through the pre-fix manifest check:
`files_total: 7, files_filtered: 6, files_kept: 1` — 6 of 7 discarded, the same shape as the
originating report's 10-of-11, with `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`
(9,470 lines) among the discarded. Post-fix the same input yields `files_filtered: 0, files_kept: 7`.

#### One stated divergence from the plan's D1 sentence

The plan says *"only config or unclassified paths are bookkeeping."* Config is dropped as written.
**`unclassified` is RETAINED**, and that is a deliberate divergence:

Dropping `unclassified` would drop every unrouted-but-real path — `.github/workflows/*.yml`,
`Dockerfile`, shell scripts, `.gitignore` — opening a fresh blind spot in M1/M2/M3. A manifest
claiming a docs-only change while a CI workflow was rewritten would pass.

⛔ **An earlier draft of this section gave a second reason that was false, and round 3 caught it.**
It argued that dropping `unclassified` would also drop all documentation and leave M1's docs
predicate unable to fire. It would not: `classify_path` returns `documentation` as its own category
for `.md`/`.adoc`, and `_DROPPED_CATEGORIES` is `(runtime_state, report, config)` — documentation is
never dropped. The conclusion was right and the reason given for it was invented, which is the worse
of the two failures, because a stated reason is what a later reader checks instead of the code.

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
- **An existing test's expected verdict changed.** `test_verdict_withheld_when_only_bookkeeping_changes`
  (round 3 renamed it from `test_pass_when_only_bookkeeping_changes`, whose name asserted the verdict
  its body had stopped making) lost `.claude/settings.local.json` from its input (that path is no longer blanket-dropped) and its
  expected M2 verdict moved `pass` → `indeterminate` (every remaining supplied path is filtered, so
  D2 withholds the verdict). Both mechanisms are the deliverables working as intended, but the fact
  that a pre-existing test's expected verdict moved is stated here explicitly.

### D5 — tests, each verified to FAIL pre-fix

`test/plan-marshall/plan-retrospective/test_footprint_oracle_classification.py` carries **25 test
functions, collecting as 25 cases**, and `test/plan-marshall/script-shared/test_extension_base.py`
gains **11 test functions, collecting as 13 cases** (two are parametrized). Both figures re-derived
against the delivered tree; a count of test *functions* and a count of *collected cases* are
different numbers and both are stated.

⚠ The stated value moved twice (6 → 18 → 25) and was wrong at each step until a verification round
caught it: round 1 found "6 oracle-API tests" where the diff added 11, and round 3 found 18 stated
where the tree held 25 — each time because the commit recording the figure had already invalidated
it. (Round 2's stale-figure finding, F8, is a different figure: the build gate's.) They are
re-derived here against HEAD rather than carried forward, which is the only thing that keeps them
true.

**The red-first record covers the 11 tests that existed when it was taken** — the file then held 11
test functions, and the recorded result is **10 failed, 1 passed**. The single pass was
`test_m3_still_recognises_the_bare_module_tests_form`, which pins pre-existing back-compat behaviour
and is a regression pin rather than a red-first test — stated rather than counted as coverage.

**The other 14 tests have no red-first record**, because each was written to close a verification
finding against code that already existed. Each was instead shown non-vacuous by mutation (below).
Naming them is more useful than counting them:

- **Round 1** added 2 — `test_unclassifiable_path_counts_as_production_for_the_mis_prune` and
  `test_documentation_alone_does_not_count_as_production`.
- **Round 2** added 5 — `TestTestRecognitionSurvivesAnOracleWithNoTestRoute`'s first three,
  `TestBranchCleanupRuleDoesNotClaimAnEmptyDiff`'s one, and
  `TestConsumerDispatchSetsAreKnownCategories`'s one.
- **Round 3** added 7 — `test_the_directory_tokens_are_boundary_anchored`,
  `test_the_two_predicates_answer_different_questions`,
  `test_docs_directory_tokens_never_classify_a_source_file`,
  `test_an_unrouted_source_file_under_references_still_counts_as_production`, and
  `TestSummarizeChecksIsTotal`'s three. It also RENAMED two —
  `test_both_checks_agree_on_test_ness` → `test_the_shared_convention_recognises_the_documented_test_shapes`
  (round 2 found the old name described something the body did not test), and, in
  `test_plan_retrospective_manifest.py`, `test_pass_when_only_bookkeeping_changes` →
  `test_verdict_withheld_when_only_bookkeeping_changes`. Neither old name exists in the tree; an
  earlier draft of this report cited both, which round 3 caught.

11 + 14 = 25, which reconciles with the collected count above.

#### Mutation campaign

Each mutation below reintroduces **the specific defect its guard names**, not a neighbouring one, and
each was reverted and the tree restored (`git diff --stat`) before the next. The table covers both
kinds of guard — those that also have a red-first record and those that do not — and **every guard
D5 lists as having no red-first record appears here by name**, which is the property that matters and
is checkable by reading the two lists against each other. A row may name more than one guard, so the
row count is not a guard count and no count is asserted.

| Mutation | Guard that caught it | Round |
|---|---|---|
| `resolve_route_role` precedence → first match | `test_production_wins_over_config_in_either_declaration_order`, `test_test_wins_over_config_in_either_declaration_order` (the adverse-order arm only) | 1 |
| `_DROPPED_CATEGORIES` gains `unclassified` (the plan-literal reading) | `test_unrouted_dotfile_path_is_retained_not_assumed_bookkeeping` | 1 |
| `_PRODUCTION_CATEGORIES` loses `unclassified` | `test_unclassifiable_path_counts_as_production_for_the_mis_prune` | 1 |
| D2 downgrade disabled | `test_majority_filtered_footprint_never_yields_a_bare_pass` | 1 |
| M3 normalization removed | `test_m3_fires_on_canonical_verify_step_shape` | 1 |
| Test-convention rung removed from `classify_path` (the B1 defect) | `test_tests_only_footprint_is_not_a_mis_prune`, `test_the_shared_convention_recognises_the_documented_test_shapes` | 2 |
| M4's `"diff is empty"` message restored (the B2 defect) | `test_fully_filtered_footprint_names_the_reduction_not_an_empty_diff` | 2 |
| A dispatch set pointed at a non-existent category | `test_dispatch_sets_are_subsets_of_the_category_vocabulary` | 2 |
| Classification rung uses the WIDE docs predicate again (the F12 defect) | `test_docs_directory_tokens_never_classify_a_source_file`, `test_an_unrouted_source_file_under_references_still_counts_as_production` | 3 |
| The unanchored routing test tokens restored (the F1 substring defect) | `test_the_directory_tokens_are_boundary_anchored` | 3 |
| `summarize_checks` drops an unknown status again (the F4 defect) | `test_every_check_is_counted_even_under_an_unknown_status` | 3 |
| `documentation` added to `_PRODUCTION_CATEGORIES` (over-correction) | `test_documentation_alone_does_not_count_as_production` | 4 |
| `production` removed from `_PRODUCTION_CATEGORIES` (over-correction) | `test_a_production_file_in_the_same_footprint_still_fails` | 4 |
| The `test` rung moved AHEAD of the oracle and of `documentation` | `test_the_two_predicates_answer_different_questions` | 4 |
| Known statuses lose their explicit zero | `test_known_statuses_report_an_explicit_zero` | 4 |
| An emitted status loses its `_STATUS_BUCKETS` row | `test_every_status_the_script_emits_has_a_named_bucket` | 4 |
| `*Spec.java` dropped from the shared name pattern | `test_the_shared_convention_recognises_the_documented_test_shapes` | 4 |

⛔ **Round 4 found this table asserting more than it covered.** Its heading claimed "every new guard
shown non-vacuous" while five guards had no row at all and a sixth appeared only under a name round 3
had renamed away — the same fix-at-n−1-of-n-sites failure, applied to the record of the campaign
rather than to the code. The six missing mutations were then run (rows marked round 4 above), which
is what makes the claim true rather than merely restated.

Two details worth recording rather than smoothing over. The precedence mutation was caught by only
**one** arm of each parametrized pair — the adverse declaration order — which is the arm that exists
for exactly that reason; the other order agrees with first-match by construction. And removing the
test-convention rung failed two guards rather than one, which is what a shared classifier should do:
the consumer-level test and the classifier-level test see the same defect from different ends.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** — production scripts and tests
changed — so the full `./pw verify` ran, over the whole branch diff, from the repository root.

**Result: `=== verify: SUCCESS ===`.** Read from the tool output, not the exit code: **20695 passed,
14 skipped** (20709 collected), and the run's own coverage line reports **COMPLETE over all six
dimensions** — mypy(production) [413 files], ruff [`marketplace/bundles`, `test`, `.claude`], SPDX
headers, plugin-doctor [marketplace-wide], mypy(test) [766 files], and module-tests [whole-tree
pytest].

⚠ **These figures are the DELIVERED tree's, re-measured after the last code change** — the PR-review
round added 8 tests, moving the total from the 20687 an earlier draft recorded. This figure has been
re-derived three times for the same reason: round 2 caught it describing a tree three production
files out of date, and the review round moved it again. A build-gate figure is only evidence about
the tree it ran against, so it is re-measured at the moment of the claim rather than carried
forward.

`UV_HTTP_TIMEOUT=600` was exported, per the lane contract's note about the wrapper's dependency
fetches; no `uv` HTTP timeout occurred. The build left no `uv.lock` churn — `git status` was checked
before staging, and every commit stages named paths rather than `git add -A`.

## Findings

Recorded **per instance**. Sources: the pre-PR verification sub-agent (rounds 1–4), the build gate,
and PR review (below).

⛔ **One defect in this report was caused by the run and caught by the run, and is disclosed rather
than quietly repaired.** Commit `8cd95a7` rebuilt the mutation-campaign table with an edit whose end
boundary fell back to the next `##` heading, silently deleting the whole of `## Build gate` and
`## Findings` — rounds 1–3's tables included — and that deletion was committed and pushed. It was
found while re-deriving the build-gate figure after the review round, by checking the section
headings actually present on disk rather than assuming the file still held what had been written
into it. The sections were restored from `42e1d90` and the one round-4 fix that had lived inside
them (the F10 row's retracted premise) was re-applied.

⭐ It is the run's own recurring failure in a new costume: **a claim about the tree, trusted instead
of re-derived.** The contract warns that filesystem claims are not covered by the diff sweeps; here
the artifact whose loss went unnoticed was the sweep's own record.

### Round 1 — 2 behavioural findings, 12 false statements, and 6 lower-severity observations

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
| F10 | round 2 | M4's "so there is nothing to push/clean" is false: a `report` or `config` entry is a tracked file that really changed | **fixed** — the finding states what it knows and stops. ⚠ Round 2's own wording of this row justified it by "only `runtime_state` is git-ignored", which round 3 then showed to be false as well (see A7) |
| F11 | round 2 | The C6 remedy landed at 1 of 4 shipped sites | **fixed** at all 4, in one uniform verifiable form |
| F13 | round 2 | D0's denominator (428) counted HEAD, including the file the fix created; the sweep ran over `origin/main`'s 427 | **fixed** — re-derived via `git ls-tree -r origin/main` |

### Round 3 — 13 false statements, 1 undeclared behavioural delta

⭐ **Round 3's distinctive signal: the n−1-of-n failure migrated from "code sites" to "code but not
the shipped doc".** Round 2's two most valuable fixes — the docs split (F12) and M4's message (F10)
— were each applied to the Python module and **not** to `standards/manifest-crosscheck.md`, which
documents the same behaviour and is the surface consumer projects read. The plan's own D4 states
that the documentation and the script must agree; for two rounds they did not.

| # | Source | Finding | Disposition |
|---|---|---|---|
| A1 | round 3 | The standards doc still stated the **pre-F12** docs rule — `references/`/`templates/` as part of the classification rung | **fixed**; the doc now states the split and why only the rung is suffix-only |
| A2 | round 3 | The standards doc still documented M4's retracted `"nothing to push/clean"` conclusion, and the documented string no longer matched the emitted one | **fixed**; a guard already asserts `'nothing to push' not in message`, so doc and guard now agree |
| A3 | round 3 | "carried over unchanged from the pre-oracle code" — the exact phrase the module's own ⛔ forbids | **fixed**; the doc now separates the halves (docs did not move; tests moved in both directions) |
| A4 | round 3 | `load_oracle_routes` claimed `classify_path` returns `unclassified` for every non-runtime-state, non-docs path — the `test` and `report` rungs also fire with no oracle | **fixed** |
| A5 | round 3 | The ⛔ block claimed unification "necessarily changed each of" the copies — false for the documentation sets, which were identical in both and did not move | **fixed** |
| A6 | round 3 | The docs-provenance claim survived at a **third** site (the `DOCS_SUFFIXES` comment), untouched by all three rounds | **fixed** |
| A7 | round 3 | **"`.plan/` is git-ignored" is false in this repository** — `git ls-files .plan/` returns 13 tracked paths including `marshal.json`, which holds `build.map` itself. 7 sites, 2 of them written by round 3. This repo's own `_plan_state_exemption.py` exists *because* a bare `.plan/` rule keyed on that premise hid tracked edits — and the report's D0 table cites that very module | **fixed at all 7**; the rung is now justified by the absence of an oracle answer, which is true, rather than by trackedness, which is not. The behaviour is unchanged and remains authorised by the plan's ⭐ |
| A8 | round 3 | `_STATUS_BUCKETS` described as covering "statuses whose bucket name differs from the status itself"; its fourth row is an identity | **fixed** |
| A9 | round 3 | D5's figures said 18/18 where the tree held 25/25 — invalidated by the same commit that recorded them, the second instance of this failure mode | **fixed**, re-derived |
| A10 | round 3 | The report cited two test names that same commit had renamed | **fixed** |
| A11 | round 3 | "Mutation campaign — every new guard shown non-vacuous" omitted round 3's 7 guards | **fixed** |
| A12 | round 3 | **D1's divergence rationale rested on an invented premise** — that dropping `unclassified` would drop documentation. It would not; `documentation` is its own category and is never dropped | **fixed**; the conclusion stands on the true reason (unrouted-but-real paths) |
| A13 | round 3 | Minor: "reduced to a single survivor" (an entirely-from-that-tree footprint leaves zero); a dangling "see the stop record below"; the round-1 heading characterised 14 of 20 rows | **fixed** |
| B1 | round 3 | `*Spec.java` in the shared name pattern is an **exonerating** delta for the routing consumer, undeclared, while the docstring claimed to name "both directions" | **fixed by declaration** — see below |

**B1 in full.** `TEST_NAME_RE` gained `*Spec.java`, which only the manifest copy carried, so
`footprint_has_production(['src/FooSpec.java'])` is `False` at HEAD and was `True` on `origin/main`
— a `no_code_delta` mis-prune moves `fail` → `pass`. The change is **deliberate and correct** (a
Spock/Spek spec is a test, and the routing copy's omission was a gap, not a policy), and it is
**bounded**: reachable only where the oracle is silent for that path, the basename matches
`*Spec.java`, and the path lies outside `test/`/`tests/`. A JVM project routes `src/test/**` as
`test`, so the oracle answers first and the rung is never consulted; this repository holds 10 `.java`
files and zero `*Spec.java`, so it cannot change this deliverable's own verdict. The defect was that
none of this was written down while the docstring claimed to name "both directions" — it is now
declared, with its direction and bound, in `TEST_DIR_TOKENS`' comment and in the standards doc.

**One correction that cannot be made where it was written.** Commit `a657691`'s message says "Adds
six guards"; it adds seven. The commit is pushed, so the message is corrected here rather than by
rewriting history.

### Round 4 — 7 false statements, 2 report defects, 0 behavioural

| # | Source | Finding | Disposition |
|---|---|---|---|
| A-1 | round 4 | The mutation table's "every new guard shown non-vacuous" was false: five guards had no row and a sixth appeared only under a retired name — so A11's own "fixed" was false | **fixed** — the six missing mutations were RUN (rows marked round 4), and the claim is now checkable name-by-name |
| A-2 | round 4 | The mutation table still cited `test_both_checks_agree_on_test_ness`, renamed away in round 3 | **fixed** |
| A-3 | round 4 | § Declared collateral still cited `test_pass_when_only_bookkeeping_changes`; A10 had landed at 1 of 3 sites | **fixed** |
| A-4 | round 4 | The F10 row restated "only `runtime_state` is git-ignored" — the premise A7 retracts twenty lines below | **fixed** |
| A-5 | round 4 | An **eighth** site, in shipped code: `_footprint_resolver.py`'s `resolve_merge_commit_footprint` docstring. Pre-existing on `origin/main`, in a file this branch modified | **fixed** — the operative conclusion holds (`.plan/archived-plans/` *is* ignored, confirmed by `git check-ignore -v`); only the blanket clause was false |
| A-6 | round 4 | The same premise in `a657691`'s pushed commit message | **corrected here** — the commit is pushed, so it cannot be corrected where it was written |
| A-7 | round 4 | The D5 note misattributed which round caught the figure errors and said "three times" for two moves | **fixed** |
| D-1 | round 4 | A blank line between the mutation table and the rows round 3 appended terminated the Markdown table, so A11's own remedy rendered as literal text | **fixed** — rebuilt as one table |
| D-2 | round 4 | The D1 rewrite duplicated a paragraph verbatim ten lines apart, against the repo's no-duplication standard | **fixed** |
| D-3 | round 4 | "A 7-path footprint of this project's own project-local production modules" — there are six; the seventh was a control | **fixed** |

### PR review — `coderabbitai`, 6 findings, all valid, all fixed

⭐ **The re-request was worth making.** `coderabbitai` was `rate-limited` at PR-open with a
clearing countdown; rather than merge on 1-of-3, the run waited for the window, posted the
registry-declared `@coderabbitai review` trigger, and got a review that found **two real defects the
four verification rounds missed** — both of them instances of the very archetype this plan exists to
remove. Neither an aborted nor an un-re-requested review would have surfaced them.

| # | Finding | Disposition |
|---|---|---|
| CR-1 | The report's wall-clock end was written `2026-08-18T00:4x` while citing `git log --date=iso-strict` as its source — a value that command never produced | **fixed** — a figure carrying precision it does not have, with a source cited for it |
| CR-2 | `_DIFF_FED_CHECKS` was a **hardcoded name set mirroring the dispatch table**. A new filtered evaluator added to one and not the other would silently bypass the reduction report and the `indeterminate` downgrade | **fixed** — one `_DIFF_FED_RULES` registry now feeds both the evaluation loop and the membership test, with four guards over it. ⛔ This is the plan's own archetype — a private list restating a set defined authoritatively elsewhere — reproduced *inside the fix for it*, in the membership test of the guarantee it protects |
| CR-3 | Both loaders tested `--diff-file` by truthiness, so an explicit `--diff-file ""` took the omitted-input path | **fixed** — `is None` / `is not None`, and an empty-or-whitespace argument is rejected by name rather than failing later as "is a directory" |
| CR-4 | `--base-ref` documented as "required when `--diff-file` is absent" with no mechanism enforcing it | **fixed by documenting the real behaviour** — the script is best-effort by contract and an existing test deliberately pins the degradation. But investigating it exposed a live defect (next row) |
| CR-5 | An **existing but empty** diff file fell through to fallback resolution: `if footprint:` treated a resolved-empty footprint as unresolvable | **fixed** — the loaders now distinguish omitted (`None`) from supplied-and-empty (`[]`) |
| CR-6 | Two guards asserted subset/iteration relations over sets that would pass **vacuously if the population became empty** | **fixed** — non-vacuity assertions precede the relations in both |

**The defect CR-4 exposed, which no reviewer asked for and no round found.** With no `--diff-file`
and no `--base-ref`, rules M1–M3 emitted a bare clean `pass` over an empty footprint — literally
`all 0 non-bookkeeping diff entries are docs-shaped`. D2's reduction logic is blind to it: nothing
was *discarded*, so the reduction is empty, yet the rule evaluated a footprint it never received.
That is the same misleading-clean-signal archetype as the plan's headline defect, reached by a third
door. Diff-fed rules now take `indeterminate` when no diff observation reached them.

⛔ **And the first fix for it repeated the conflation it was closing.** The predicate was written as
`len(raw_files) > 0`, which reads an ABSENT observation and a RESOLVED empty one as the same state —
so a supplied diff file that legitimately names nothing would have had its rules' verdicts withheld.
An existing test caught it. The loader now reports evidence-availability directly rather than
leaving it to be inferred downstream, and both states are pinned by test.

Every finding was mutation-tested where it produced a guard: reverting to `len(raw_files) > 0` fails
the supplied-empty control, and removing the withholding fails the no-evidence guard.

**No comment was left unaddressed**, and none was rejected — all six were valid.

### When the loop stops

**The loop ended on the BUDGET exit, not on a verifier's "nothing remains".** The budget — **four
rounds** — was declared before the first dispatch, and round 4 was the fourth. Its answer to the stop
question was *"Yes — condition A forbids leaving seven of these open."* Everything condition A
forbids was then fixed regardless of the budget, as A requires, and **those fixes have not themselves
been put to a verifier.** That is the honest shape of this stop and it is stated rather than dressed
as convergence.

**What the rounds actually found, round by round** — this is the observation the contract asks for,
and it does not read as steady convergence until the last round:

| Round | Behavioural | False statements | Where they were |
|---|---|---|---|
| 1 | 2 | 12 (+6 lower-severity) | the shipped change |
| 2 | 1 | 12 | the shipped change, incl. a regression round 1 created and denied |
| 3 | 1 undeclared delta | 13 | the shipped doc and module — **the same breadth as round 2** |
| 4 | 0 | 7 (+2 defects) | **5 of 7 in this report**; 1 pre-existing, 1 an immutable commit message |

**Round 4's findings ARE narrower, and rounds 2 and 3's were not.** Round 3 explicitly reported "No"
to the narrowing question — same breadth, same location. Only round 4 turned: zero findings in the
delivered behaviour, in the tests, in the standards doc, or in the code that round wrote. That
turn came one round before the budget ran out, which is a thinner margin than it looks.

**The evidence round 4 rested on was stronger than another read.** It ran an
`origin/main`-vs-HEAD differential over **2,871 paths** (`git ls-files` at HEAD ∪ `git ls-tree -r
origin/main` ∪ 55 adversarial synthetics), evaluating each as a single-path footprint against
`origin/main`'s transcribed predicates and HEAD's live classifier. Twenty-three paths differ: 18
fail-closed (the deliverable, plus the substring-defect paths) and 5 exonerating — `FooSpec.java` in
four spellings and `pyproject.toml` under a `config` route. **No undeclared exonerating delta
exists.** It also fuzzed `summarize_checks` over randomized populations, re-derived every figure from
its source, and re-ran the four affected test files.

#### The one survivor

| Survivor | Kind | Why it may stay open |
|---|---|---|
| `*Spec.java` recognised by the shared name pattern | Behavioural, **exonerating** for the routing consumer | **(b) bounded.** A footprint of only `src/FooSpec.java` counted as production before and is `test` now, so a `no_code_delta` mis-prune moves `fail` → `pass`. The change is deliberate and correct — a Spock/Spek spec *is* a test, and the routing copy's omission was a gap, not a policy. **The bound:** reachable only where the oracle is silent for that path AND the basename matches `*Spec.java` AND the path lies outside `test/`/`tests/`. **The promise:** a JVM project routes `src/test/**` as `test` (`build-maven/scripts/extension.py`), so the oracle answers first and the rung is never consulted. |

Round 4 was asked to verify that declaration and did: direction named at three sites, bound stated,
and **the bound verified TRUE by execution** — `test/FooSpec.java` and `src/test/java/FooSpec.java`
show no delta on either side, and `[^/]+Spec\.java` is the only alternation added to `TEST_NAME_RE`.
It judged the bound conservative (it omits "and not under `.plan/`/`.claude/`", which only shrinks
the true delta region). This repository holds 10 `.java` files and **zero** `*Spec.java`, so the
survivor cannot change this deliverable's own verdict.

No behavioural finding was left `deferred`.

#### What residue to assume remains

⛔ **Do not read this as a defect-free deliverable.** Read it as one whose last round found nothing
in the shipped change and seven false statements in the record of it — so residue of *that* kind
should be assumed to remain.

Round 4's own answer, which is the more useful form: the residue has one shape — **a correction
applied to the body of a claim but not to every place the claim is restated.** That shape recurred in
all four rounds and simply migrated: code sites (round 2), code-but-not-the-shipped-doc (round 3),
then the report's own body-but-not-its-tables (round 4). A reader should treat any *count*, *guard
name*, or *"fixed at all N"* disposition in this report as possibly one site short, and re-derive it
rather than trust it. Every such claim round 4 re-derived — three of them — failed.

One shipped file carries a related falsehood this plan did not own and did not introduce:
`_footprint_resolver.py`'s blanket "`.plan/` is git-ignored", pre-existing on `origin/main`. It was
corrected here because the file is in this diff, not because the plan reached it.

`Outcome` above reports the **deliverables**, not the loop: all six are complete and verified. The
loop's own exit is recorded here, separately, as the budget exit it was.

## Reviewer participation

**Population derived from configuration, not transcribed.** Every
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
declaring an `author_login`: `coderabbit.md` → `coderabbitai`, `pr-agent.md` → `cuioss-review-bot`,
`sourcery.md` → `sourcery-ai`. Cross-named by `.github/workflows/pr-agent.yml`. **M = 3.**

All THREE comment surfaces were read — `get_comments` (issue comments), `get_reviews` (review-summary
bodies) and `get_review_comments` (inline threads) — because none subsumes the others on the MCP
path. Each verdict below comes from a stored body, never from a check-run state.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence |
|---|---|---|---|
| `cuioss-review-bot` | `reviewed` | — | Issue comment on head `8cd95a7`: "PR Reviewer Guide 🔍 — PR contains tests / No security concerns identified / **No major issues detected**". A review artifact against the diff carrying an explicit nothing-to-report. Its `review / review` check also concluded `success`, but that is not what the verdict rests on |
| `coderabbitai` | **`reviewed`** (recovered) | — | Initially `rate-limited` / `Reopens? yes` — "Review limit reached … **Next review available in: 28 minutes**", re-issued against head `622c052` at 00:45:53Z. The run waited out the countdown and posted the registry's `trigger_comment` (`@coderabbitai review`); it acknowledged at 01:13:09Z ("I will review pull request #1288 at head `622c052`") and filed **6 inline review threads** at 01:19:38Z, plus a walkthrough appended to the PR body |
| `sourcery-ai` | `rate-limited` | **no** | Review-summary body: "your pull request is larger than the review limit of **150000 diff characters**". A property of THIS diff, not of the clock — the same request never succeeds at this size, so waiting is futile. Its `Sourcery review` check concluded `skipped`, consistent with the body |

**Coverage: 2 of 3** after the recovery, from 1 of 3 at PR-open. No verdict is `silent`, so no
recovery check of that kind was owed; no verdict is `unreadable`, so merge-gate condition 2 is
**established on evidence** rather than overridden — all three surfaces returned successfully, and
`comments: 1` on the PR payload served as a positive control that bodies existed before any of them
was read.

⚠ **Which head each reviewer actually saw, stated rather than glossed.** `cuioss-review-bot`
reviewed `8cd95a7` and `coderabbitai` reviewed `622c052`; the head is now `ad14fee`. **Both are
behind it, and by real code** — the commit closing `coderabbitai`'s six findings changed four bundle
files and three test files, so neither verdict covers the current head in full. Neither re-ran:
there is no `review / review` check on the new head, and `coderabbitai` states it "does not
re-review already reviewed commits".

What that leaves is honest to say and worth saying plainly: **the delivered head carries changes no
reviewer has seen**, all of them made in response to review, all covered by the local gate
(`./pw verify`, 20695 passed) and by mutation-tested guards, but not re-reviewed. Pushing again to
re-trigger would restart the same cycle against a head that would itself move; that is a reason to
disclose the gap, not to hide it.

⭐ **The one remaining shortfall does not reopen.** `sourcery-ai`'s refusal is a 150,000-character
diff-size ceiling — a property of this diff, not of the clock. Re-requesting never succeeds at this
size, so no recovery attempt is owed or was made. `coderabbitai`'s shortfall was the other kind and
*was* recovered; recording both under a bare `rate-limited` would have hidden which was which.

**Actionable comments: 6, all from `coderabbitai`, all valid, all fixed and answered** — see
§ PR review above for each finding and its disposition. Every thread received a reply naming the
commit and what changed, and all six were resolved. None was rejected. The inline review-thread
surface was empty at PR-open (`totalCount: 0`) and carried these six after the re-request; an earlier
draft of this paragraph recorded the empty reading as final, which the re-request then falsified.

**§ Step 8 condition 4 disclosure fired**, before arming auto-merge, in these words: *"Review
coverage: 2 of 3 — `cuioss-review-bot` reviewed with no issues (at head `8cd95a7`); `coderabbitai`
reviewed after a re-request and filed 6 findings, all fixed (at head `622c052`); `sourcery-ai`
rate-limited on a 150,000-character diff-size ceiling, which does not reopen. The delivered head
`ad14fee` carries the fixes for those 6 findings and has not itself been re-reviewed."* A run that
merges on 2-of-3 must say 2-of-3, and must say which head the 2 saw.

## Cost

- **Tokens:** **not available to the agent in this session.** The harness does not expose a token
  count to the running agent, and no figure is invented in its place.
- **Wall-clock:** first commit `dfa4c56` at **2026-08-17T21:18:20+00:00**; the review-cycle commits
  continue past it, so no single end timestamp is quoted here — the PR's own merge event is the
  authoritative end. Both figures are `git log --date=iso-strict` output verbatim. Elapsed time on
  the branch includes four `./pw verify` runs (~8 minutes each), four dispatched verification rounds,
  and the review cycle.

  ⚠ An earlier draft wrote the end as `2026-08-18T00:4x` while naming `git log --date=iso-strict` as
  its source — a value that command never produced. `coderabbitai` caught it. A figure carrying a
  precision it does not have is the same defect as a wrong figure, and citing a source for it is
  worse.
- **Population:** what these figures count is **this single Claude Code cloud session**, as the
  session's own clock records it. ⛔ **Not comparable to a plan-marshall `metrics.toon` total.** That
  counts the orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing
  boundary, which a single interactive cloud session does not share — there is no dispatch tree here,
  the verification sub-agents are Task-tool children rather than billed leaf dispatches, and no
  ledger records them. The figures cannot be made comparable, so no comparison is offered.

## Contract check (Step 9)

Re-read against what actually happened, confirming both that each step ran and that its artifact
exists on disk.

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **done** | Named in § Skills loaded. Loaded by bundle path — the `plan-marshall` plugin is not installed in this session, so `Skill:` notation was not used. No skill was unobtainable by both routes |
| 2 Branch | **done** | `claude/manifest-cross-check-production-edn4tw` — **harness-assigned**, kept as-is per the contract. Published to `origin` before the first edit: `git ls-remote` was empty, so the branch was pushed as the run's first action |
| 3 Plan directory | **done** | `doc/plans/code-intelligence-substrate/320-manifest-cross-check-discards-production-tree/plan.md` exists and opens with the first-instruction block (present on arrival — no repair needed). The `320-` priority prefix is preserved by the move |
| 4 Implement | **done** | Six commits, each carrying the `Co-Authored-By: Claude` trailer and no "Generated with Claude Code" footer. All six deliverables addressed |
| 4 Per-commit gate | **done** | Every commit touching `*.py` was preceded by a clean gate — the direct `./pw` path, so read from the streamed tool output: `ruff … All checks passed!`, `mypy … Success: no issues found in 413 source files`, `SPDX-header check passed`, `issues[0]` |
| 4 Pushed | **done** | Pushed after every commit, not once at PR time. `git status -sb` reports no `ahead` at the final commit |
| 5 Build gate | **done** | Git-derived verdict recorded (§ Build gate): `*.py` changed ⇒ full `./pw verify`; result `20695 passed, 14 skipped`, coverage COMPLETE over all six dimensions. Re-measured on the delivered tree each time the tree moved — round 3 caught this figure describing a superseded tree, and the PR-review round moved it again |
| 6 Verification sub-agent | **done** (and partly overtaken) | Four rounds, budget declared before the first dispatch. Findings and dispositions per instance above; the stop record names the **budget exit**, the round that ended it, round 4's own last answer, the evidence it rested on (a 2,871-path differential), that rounds 2–3's findings were **not** narrower and round 4's were, the single survivor with its (b) bound, and the residue to assume remains. ⚠ The loop's verdict was then **partly overtaken by PR review**: `coderabbitai` found two real defects the four rounds missed. Recorded as the loop's limit rather than as a failure of it — a reviewer whose method differs is worth having, which is why the run waited out its rate window instead of merging without it |
| 7 PR cycle | **done** | PR [#1288](https://github.com/cuioss/plan-marshall/pull/1288). No `skip-bot-review` label: the diff touches `*.py` **and** `marketplace/bundles/**`, and a skill is code. All three surfaces read; participation table carries a verdict **and** a `Reopens?` value per reviewer; no `silent` verdict, so no recovery check of that kind was owed; no `unreadable` verdict, so condition 2 is established on evidence. `coderabbitai`'s 6 comments were each fixed, replied to naming the commit, and resolved |
| 8 Merge gate | see below | |
| 8 Bridge | **done** | No status or bookkeeping write landed under `doc/plans/` outside this plan's own directory — no ledger, no status file, no other plan's directory touched. The report carries the PR number and a per-deliverable outcome for the orchestrator to collect |
| 9 This check | **done** | This table |
| 9 What have we learned | **done** | Below |

**GitHub access path:** the **GitHub MCP server**. There is no `gh` CLI in this session; the `gh`
spellings in the contract were mapped to `pull_request_read` (`get`, `get_comments`, `get_reviews`,
`get_review_comments`, `get_check_runs`) and `create_pull_request`.

**Branch form:** harness-assigned `claude/*`, kept. The closed prefix set governs branches a run
creates; this run created none.

**Plugin cache sync:** **not owed.** `/sync-plugin-cache` is a machine-local build step reading the
git-ignored `target/` and writing `~/.claude/`; a cloud run neither performs nor records one, even
though this diff edits `marketplace/bundles/`.

**Tree claims re-verified at the end, not recalled.** Claims about the *filesystem* are not covered
by the diff sweeps, and this run's own build gate mutates the tree it describes. Re-derived:

- `git status -sb` reports no `ahead` — nothing unpushed;
- **no `uv.lock` churn in any commit** — every commit staged named paths, never `git add -A`;
- every commit carries the `Co-Authored-By: Claude` trailer, and **no** commit carries a "Generated
  with Claude Code" footer (`git log --format=%B | grep -c` → 0);
- **no write under `doc/plans/` outside this plan's own directory** — the bridge rule, checked by
  diffing the path set rather than asserted;
- the build runs created `.plan/execute-script.py`, `.plan/local/` and `.plan/temp/`, plus
  `__pycache__` trees. All are git-ignored and reached no commit. Recorded because the tree at the
  end of the run is not the tree it started with, and a report describing the starting tree would be
  false by the time anyone read it.

⛔ **One tree claim in this report was false and was caught by exactly this check** — see the
disclosure at the head of § Findings. Two whole sections had been deleted by an earlier edit of this
file and shipped that way. Nothing in the diff sweeps could see it: the loss was in the artifact
doing the describing.

## What have we learned (Step 9)

**One contract change is proposed, and it is presented to the operator rather than self-approved.**

### The evidence this run produced

The contract's § Step 6 tells a run to sweep by **consumer kind** and lists them: prose, docs, tests,
`*.py` fixtures and stubs, prose-bearing string literals in production code. This run swept exactly
that way and still leaked the same class four rounds running — but the leak was never a *kind* the
list omits. It was always the same kind, at a site the sweep had not enumerated:

| Round | The correction | Where it did not land |
|---|---|---|
| 2 | docs-provenance claim | a third site **in the same file**, 30 lines from the ⛔ that forbids it |
| 3 | the F12 docs split, and M4's message | `standards/manifest-crosscheck.md` — the shipped doc for the same behaviour |
| 4 | the mutation-campaign claim, and two renamed test names | the report's own **tables**, while its body was correct |

The contract already names this ("Sweep-and-count: a claim is corrected at every site or it is not
corrected") and even prescribes the remedy — *grep for the claim before fixing any instance of it*.
What it does not say is **what the enumeration must cover**, and every miss above was an enumeration
that stopped at the artifact kind the fix lived in: the code, not the doc that documents the code;
the prose, not the table that tabulates the prose.

### The proposed edit

Add to § Step 6's sweep-and-count block, after "Grep for the claim before fixing any instance of it":

> ⛔ **The enumeration crosses artifact kinds, and that is where it keeps stopping.** A claim
> corrected in code is not corrected until the doc that documents that code says the same thing, and
> a claim corrected in prose is not corrected until every table, index, or disposition row that
> restates it does too. Three consecutive rounds of one observed run each caught a fix that had
> landed in one kind and not the neighbouring one — code but not the shipped standards doc, prose but
> not the table below it — while the run was diligently sweeping *within* each kind. So enumerate the
> claim's sites **by artifact kind first** (code, its shipped doc, the tests, the report's prose, the
> report's tables), then grep within each.

### Ship it separately

On approval this ships as its own `chore/` branch touching only `.claude/skills/cloud-plan-lane/SKILL.md`,
**without** `skip-bot-review` — it changes a skill, and a skill is code that gets reviewed. It is
deliberately kept out of this plan's PR: two changes with different review audiences in one diff
means neither gets read properly, and it would couple a contract amendment to whether this plan lands.

**Operator disposition:** *pending* — the run is autonomous, so this is recorded as proposed and
unapproved. It has not been shipped.

## Residue

**Nothing in this plan's scope is left unfinished.** All six deliverables are complete, verified per
site where the plan required it, and covered by tests that were shown non-vacuous. What follows is
residue in the strict sense: things a later reader should know, not work this run skipped.

| Residue | Where it should go next |
|---|---|
| **The survivor.** `*Spec.java` recognised by the shared name pattern is an exonerating delta for the routing consumer, bounded and declared (§ When the loop stops). It cannot fire on this repository | Nowhere, unless a consumer project appears whose `build.map` is silent for a `*Spec.java` outside `test/` — then the bound is the thing to re-check |
| **The record's own defect class.** Every round found a correction applied to a claim's body but not to every place it is restated. A reader should re-derive any *count*, *guard name*, or *"fixed at all N"* disposition in this report rather than trust it | The proposed contract change (§ What have we learned), if the operator accepts it |
| **`_footprint_resolver.py`'s `.plan/` clause** was corrected here because the file is in this diff, not because the plan reached it. Sibling modules may carry the same blanket "`.plan/` is git-ignored" premise | A `chore/` sweep for that premise across the tree, if anyone wants it. Out of this plan's scope |
| **The oracle itself is unconsolidated.** This plan is one *consumer* adopting `build.map`; the plan's Out-of-scope says so explicitly. `resolve_route_role` is a consumer-side lookup, not the consolidation | Whichever plan owns oracle consolidation |
| **Two more private copies of the canonical-verify `verify:` prefix knowledge** exist (`manage-config/scripts/_cmd_quality_phases.py::_CANONICAL_VERIFY_PREFIXES`, `tools-marketplace-inventory/scripts/_dep_detection.py::CANONICAL_COMMAND_PREFIXES`), and D3 added a third normalizer locally rather than sharing one. This is the same source-of-truth-duplication archetype as the defect this plan fixed, but for *step ids* rather than *paths*, so it fell outside D0's stated scope (`"is this path implementation"`) | A follow-up plan, scoped to step-id classification. Named here so it is not rediscovered from scratch |
| **The delivered head `ad14fee` has not been re-reviewed.** Both reviewers that reviewed saw earlier heads, and the commit closing `coderabbitai`'s six findings changed four bundle files and three test files | Disclosed at § Reviewer participation and in the § Step 8 condition 4 statement. Covered by the local gate and by mutation-tested guards, but not by a reviewer. Re-triggering would restart the cycle against a head that would itself move |
| **`sourcery-ai` never reviewed this diff** and cannot at this size — a 150,000-character ceiling, which does not reopen | Nothing to do here. A future plan wanting Sourcery coverage of this surface would have to land it in smaller pieces |
