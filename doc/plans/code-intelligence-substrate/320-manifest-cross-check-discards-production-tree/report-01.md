# Run report — 320-manifest-cross-check-discards-production-tree (run 01)

**Date (UTC):** 2026-08-17 – 2026-08-18    **Branch:** `claude/manifest-cross-check-production-edn4tw` (harness-assigned)    **PR:** TBD    **Outcome:** completed

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

## Cost

## Contract check (Step 9)

## What have we learned (Step 9)

## Residue
