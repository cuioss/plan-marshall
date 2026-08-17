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

**Population found: 2. Components examined: the full `*.py` corpus of `marketplace/bundles/` and
`.claude/`** (the two trees that can hold a classifier), swept along five independent dimensions so
the answer is not one grep's blind spot:

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

A `fail` is never downgraded (a violation in the surviving fraction is still a violation); a `skip`
is never downgraded (the rule did not apply, which filtering did not decide). The `diff` block now
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

### D5 — tests, each verified to FAIL pre-fix

`test/plan-marshall/plan-retrospective/test_footprint_oracle_classification.py` (13 tests) plus 6
oracle-API tests in `test/plan-marshall/script-shared/test_extension_base.py`.

**Recorded red-first run** (shared module written, no consumer wired): **10 failed, 1 passed**. The
single pass was `test_m3_still_recognises_the_bare_module_tests_form`, which pins pre-existing
back-compat behaviour and is a regression pin rather than a red-first test — stated rather than
counted as coverage.

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

All five mutations were caught; every mutation was reverted and the tree restored before proceeding.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** — production scripts and tests
changed — so the full `./pw verify` ran. Result recorded below the build section of this report at
the commit that carries it.

## Findings

## Reviewer participation

## Cost

## Contract check (Step 9)

## What have we learned (Step 9)

## Residue
