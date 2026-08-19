# Verification — 320-manifest-cross-check-discards-production-tree

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** the plan landed as `eb0124c` (`fix(plan-retrospective): consult the build-map oracle instead of a private prefix list (#1288)`), audited in the working tree of branch `claude/code-intelligence-substrate-analysis-kah884` (HEAD moved during the audit as sibling audit agents committed — `57b5cd1` → `38fd31d`; none of those commits touch this plan's surfaces). `check-routing-decisions.py`, `SKILL.md` and `references/routing-decision-verification.md` have been further edited by later plans (#1293, #1295); everything asserted below was read from the tree as it stands now.
**Overall verdict:** CONFIRMED WITH GAPS

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | Derive the population of private classification lists | 2 sites; 427 `*.py` examined on `origin/main`, 428 on HEAD | Both re-derived exactly (427 / 428, the single added file being `_footprint_classification.py`); an independent five-way sweep finds no third site | CONFIRMED |
| D1 | Replace the private prefix lists with an oracle lookup at every site | Both sites now share `_footprint_classification`; new `read_build_map_routes` / `resolve_route_role` in `extension_base` | `_BOOKKEEPING_PREFIXES` exists nowhere in the tree but as a quoted historical example; both consumers import the shared module; mutation reintroducing the private rule turns both per-site guards red | CONFIRMED (one declared divergence — `unclassified` retained) |
| D2 | A rule whose input set was reduced must report the reduction | `apply_input_reduction` annotates every diff-fed check, downgrades a would-be bare pass to `indeterminate` | Verified adversarially by running the script: 5-of-6 discarded ⇒ `indeterminate` + `VERDICT WITHHELD`; disabling the downgrade turns two guards red | CONFIRMED |
| D3 | Fix the unreachable rule (M3) | M3, not M4; `normalize_verification_step` strips `default:` then `verify:` | The composer's Rule 4 (`tests_only`) really does emit `['verify:module-tests']`; disabling the normalization turns four tests red | CONFIRMED |
| D4 | A supplied-but-unresolvable path fails loudly or resolves as documented | `resolve_diff_file_path` resolves plan-dir-first, cwd-second, else raises; adopted by both scripts | Confirmed in source and by mutation (dropping the plan-dir candidate turns the equality guards red). Two documentation surfaces still disagree with the script — see G1 and G6 | CONFIRMED WITH GAPS |
| D5 | Tests, each verified to FAIL pre-fix | 25 test functions / 25 collected in the new file; 11 / 13 in `test_extension_base.py` | The extension-base figures are exact. The oracle file holds **31** test functions and collects **31** cases at the delivering commit and now — the report's re-derivation claim is false (G4, G5). The tests themselves are real and non-vacuous | CONFIRMED (deliverable) / REFUTED (the report's count of it) |

## Per-deliverable detail

### D0 — GATE: the population of private classification lists

- **Required (plan):** "the population is enumerated from source and published", with the count found reported separately from the number of components examined.
- **Claimed (report):** population 2 (`check-manifest-consistency.py`, `check-routing-decisions.py`); 427 components examined on `origin/main`, 428 on HEAD, the extra being the file the change created; five candidates examined and excluded with reasons.
- **Found / checks run:**
  - `git ls-tree -r --name-only eb0124c^ | grep -E '^(marketplace/bundles/|\.claude/).*\.py$' | wc -l` → **427**; the same on `eb0124c` → **428**. `diff` of the two listings yields exactly one added path: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/_footprint_classification.py`. Both figures and the identification are exact.
  - Independent sweep for a third site: `_BOOKKEEPING_PREFIXES` (0 live occurrences), `*_PREFIXES` constants across `marketplace/bundles/` + `.claude/` (13 hits, none a path-implementation classifier), `def is_*_path` / `classify_*` predicates, and hardcoded `.claude/` strings (all path *locators*, not classifiers). `.claude/skills/*/scripts/*.py` carries no such list either.
  - The two nearest non-members were checked rather than assumed: `manage-execution-manifest/_manifest_core.py` classifies only what no build extension claimed (documentation by suffix, infra config by family) and runs *after* the extensions, so it is an owner-less fallback rather than a private copy of the oracle; `check-artifact-consistency.py` carries no path classification at all.
- **Verdict:** CONFIRMED. The published population is 2 and my sweep finds no third.

### D1 — replace the private prefix lists with an oracle lookup, at every site

- **Required (plan):** each site queries the oracle, asserted per site; "a path whose resolved role is production or test is implementation; only config or unclassified paths are bookkeeping"; the runtime state directory may stay hardcoded.
- **Claimed (report):** both consumers share `_footprint_classification`; `read_build_map_routes()` / `resolve_route_role()` added to `extension_base`; the LOAD-BEARING oracle claim read from source; reproduced in the clone (7-path footprint: pre-fix 6 dropped, post-fix 0).
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/extension_base.py:412` `read_build_map_routes`, `:489` `resolve_route_role` (precedence `production ▸ test ▸ config` over the *matched set*, so order-independent), `:534` `_read_build_map_globs` derived from the same reader.
  - `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/_footprint_classification.py:267` `classify_path`; consumed at `check-manifest-consistency.py:234` `filter_bookkeeping` and `check-routing-decisions.py:416` `footprint_has_production`.
  - LOAD-BEARING claim verified from two directions: `.plan/marshal.json`'s `build.map` really routes `.claude/skills/*.py` → `production`, and `build-pyproject/scripts/extension.py:52-70` `_project_local_skill_globs()` emits `(f'{root}/*.py', 'production')` for every `marketplace_paths.get_project_skill_roots()` root (line 265 splices it into `classify_globs`).
  - Reproduction re-run by me in this clone (importing `filter_bookkeeping` directly with the repo's real `marshal.json`): a 7-path footprint of the six `.claude/skills/*/scripts/*.py` production modules plus one `marketplace/bundles/` control ⇒ `supplied 7 kept 7 dropped 0`, `by_category {'production': 7, …}`, `oracle_available True`. The report's post-fix figure is exact, and "there are six" project-local modules is exact.
- **Checks run (mutation):** adding `or path.startswith('.claude/')` to `classify_path`'s runtime-state rung — the pre-fix rule, reintroduced — turns **four** guards red across the four affected test files, including one per site: `TestProjectLocalTreeSurvivesFilter::test_multi_file_project_local_footprint_is_not_filtered` (manifest site), `::test_routing_check_sees_project_local_production` (routing site), `::test_runtime_state_directory_is_still_bookkeeping`, and `test_plan_retrospective_manifest.py::TestEarlyTerminateRule::test_unrouted_dotfile_path_is_retained_not_assumed_bookkeeping`. (The original audit stated three, having counted only the failures inside `test_footprint_oracle_classification.py`; the fourth lives in the sibling file. Re-measured under adversarial review, and also under the stronger equivalent mutation `RUNTIME_STATE_PREFIXES = ('.plan/', '.claude/')`, which gives the same four.) File restored from a byte snapshot; `git status --porcelain` clean for it.
- **Divergence, declared by the run and confirmed here:** the plan's literal sentence makes `unclassified` bookkeeping; the shipped `_DROPPED_CATEGORIES` is `(runtime_state, report, config)` and **retains** `unclassified`. The run declares this and gives a true reason (dropping it would discard unrouted-but-real paths such as `.github/workflows/*.yml`). The direction is fail-closed — it can only widen what a rule sees — and it is pinned by `test_unrouted_dotfile_path_is_retained_not_assumed_bookkeeping`. `report` is also dropped, which the plan sentence does not name; that is pre-existing behaviour (`_REPORT_NAME_RE` at `eb0124c^`), not a new deviation.
- **Verdict:** CONFIRMED, with the divergence labelled rather than waved through.

### D2 — a rule whose input set was reduced MUST report the reduction

- **Required (plan):** a reduced input set produces either a reported reduction or an `indeterminate` verdict — never a bare pass; verified adversarially.
- **Claimed (report):** `apply_input_reduction` runs after every evaluator; every diff-fed check carries the reduction; a would-be bare clean pass under `files_filtered > files_kept` becomes `indeterminate` prefixed `VERDICT WITHHELD`; `filtered_by_category` / `oracle_available` / `majority_discarded` published; `summary` gains `indeterminate`.
- **Found:** `check-manifest-consistency.py:608` `apply_input_reduction`, called once at `:769` after every evaluator; `:529` `_DIFF_FED_RULES` is the single registry and `:537` `_DIFF_FED_CHECKS = frozenset(_DIFF_FED_RULES)` is derived from it (the CR-2 fix, guarded by four tests at `test_footprint_oracle_classification.py:812-865`); `:581` `_withhold_on_absent_evidence` covers the zero-evidence case CR-4 exposed.
- **Checks run:** the adversarial case run for real (5 of 6 discarded) gives `docs_only_diff: indeterminate` with the counts in the message and `summary.indeterminate == 1`; the negative control (`test_unreduced_footprint_still_passes_cleanly`) keeps an ordinary `pass`. Mutation `if check['status'] == 'pass' and False:` turns `test_majority_filtered_footprint_never_yields_a_bare_pass` **and** `test_verdict_withheld_when_only_bookkeeping_changes` red. Restored from snapshot.
- **Verdict:** CONFIRMED.

### D3 — fix the unreachable rule in the same file

- **Required (plan):** the rule fires on the composer's actual step-list shape.
- **Claimed (report):** the unreachable rule is M3 (`evaluate_tests_only`), not M4; fixed by `normalize_verification_step`; the bare form still accepted; the pre-fix fixtures drove M3 with a shape production never produces and were corrected.
- **Found:** `check-manifest-consistency.py:378` `normalize_verification_step` (strips `default:` via the shared `canonicalize_step_key`, then `verify:`), applied at `:411`. The composer side checks out: `_manifest_core.py:295` `DEFAULT_PHASE_5_STEPS = ('verify:quality-gate', 'verify:module-tests')`; `manage-execution-manifest.py:1937` normalizes candidates with `canonicalize_step_key` (which strips only `default:`); `_manifest_decide.py:188-201` Rule 4 narrows phase 5 to the module-tests role, so `['verify:module-tests']` is a shape production really emits — M3 is reachable now and was not before. M4's premise also checks out: `phase_6.steps` carries the bare `branch-cleanup`, so M4 was never the unreachable one.
- **Checks run (mutation):** disabling the prefix strip (`if False and bare.startswith(...)`) turns four tests red — `test_m3_fires_on_canonical_verify_step_shape`, `test_m3_passes_when_the_diff_really_is_tests_only`, and both `TestTestsOnlyRule` fixtures in `test_plan_retrospective_manifest.py`. `test_m3_still_recognises_the_bare_module_tests_form` stays green, confirming back-compat is a separate, live path. Restored from snapshot.
- **Verdict:** CONFIRMED.

### D4 — a supplied-but-unresolvable path fails loudly or resolves as documented

- **Required (plan):** the documented invocation and the absolute-path invocation produce the same verdict; do not report skip; the documentation and the script must agree.
- **Claimed (report):** `_footprint_resolver.resolve_diff_file_path` resolves plan-dir-first, cwd-second, and raises naming every candidate; adopted by both scripts; equality asserted by `test_documented_relative_form_matches_the_absolute_form`.
- **Found:** `_footprint_resolver.py:60-111` — absolute used verbatim; empty/whitespace argument rejected by name; relative tried as `plan_dir / raw` then `Path.cwd() / raw`; otherwise `ValueError` listing both candidates. Adopted at `check-manifest-consistency.py:194` and `check-routing-decisions.py:409`. Both loaders test `diff_file is None` rather than truthiness (CR-3), and the routing loader returns `[]` for a supplied-empty file so `cmd_run` (`check-routing-decisions.py:750-756`) keeps `have_footprint=True` (CR-5).
- **Checks run (mutation):** `candidates = [Path.cwd() / raw]` turns **three** guards red — `test_documented_relative_form_matches_the_absolute_form`, `test_manifest_check_also_resolves_the_relative_form`, and `test_check_routing_decisions.py::TestLoadDiffFiles::test_relative_argument_resolves_against_the_plan_directory` (the third was missed by the original audit's count and re-measured under adversarial review). Restored from snapshot.
- **Verdict:** CONFIRMED for the script. The "documentation and the script must agree" half is **not** fully discharged: `check-manifest-consistency.py:836`'s `--base-ref` help still asserts *"Required when `--diff-file` is absent."* while `SKILL.md:483` was corrected to the real (best-effort, unenforced) behaviour — the CR-4 fix landed at 1 of 2 sites (G1). And the only documented capture invocation of the manifest check (`SKILL.md:263-266`) passes neither `--diff-file` nor `--base-ref`, so as documented every diff-fed rule now returns `indeterminate` (G6).

### D5 — tests, each verified to FAIL pre-fix

- **Required (plan):** four named tests (a)-(d), each verified to fail pre-fix.
- **Claimed (report):** `test_footprint_oracle_classification.py` carries "**25 test functions, collecting as 25 cases**"; `test_extension_base.py` gains "**11 test functions, collecting as 13 cases**"; "Both figures re-derived against the delivered tree".
- **Found:**
  - (a) `test_multi_file_project_local_footprint_is_not_filtered` — `test_footprint_oracle_classification.py:112`; (b) `test_majority_filtered_footprint_never_yields_a_bare_pass` — `:262`; (c) `test_m3_fires_on_canonical_verify_step_shape` — `:330`; (d) `test_documented_relative_form_matches_the_absolute_form` — `:429`. All four exist and all four go red under a mutation that reintroduces the defect each names (above).
  - `test_extension_base.py`: the merge commit adds exactly 11 `def test_` functions, two of them parametrized, and pytest collects **13** cases for those names. Both halves of that claim are exact.
  - `test_footprint_oracle_classification.py`: `grep -c 'def test_'` → **31**, and `pytest --collect-only -q` → **31 tests collected**. The same file at `eb0124c` also holds 31 (`git show eb0124c:… | grep -c 'def test_'` → 31), and no commit has touched it since. The stated 25/25 is therefore false against the delivered tree, not merely stale against a later one. The six unaccounted tests are exactly the PR-review round's additions (`TestDiffFedRuleRegistryIsTheSingleSource` ×4, `TestVerdictWithheldWhenNoDiffEvidenceExists` ×2), i.e. the figure was correct at round 4 and was not re-derived after the review round — the run's own declared failure mode, one section away from where it says so.
  - Every one of the 25 guard names the report cites (D5 prose + mutation table) exists in the tree; I checked all 25 individually. No renamed-away name survives.
- **Verdict:** the deliverable is CONFIRMED; the report's measurement of it is REFUTED (G4, G5).

## Correctness review

I read `_footprint_classification.py`, `check-manifest-consistency.py`, `check-routing-decisions.py`, `_footprint_resolver.py` (resolution half) and `extension_base.py`'s new oracle API in full, plus `standards/manifest-crosscheck.md` and the two SKILL.md surfaces. Three defects, all confirmed by running the code rather than by reading it:

1. **`evaluate_branch_cleanup` reports an absence the record contradicts** — `check-manifest-consistency.py:476-481` skips on `base_label == 'unknown' or raw_files_total == 0` with the message *"rule M4 skipped — no diff data available (base=unknown or empty diff)"*. Since CR-5, a **supplied** diff file naming nothing is a *resolved* empty footprint: `cmd_run` publishes `diff_available: True` for it, but M4 is not given that signal (`:760-762` passes only `base_label` and `len(raw_files)`). Observed by running the script against an empty `--diff-file`: `diff: {… 'files_total': 0, 'diff_available': True}` beside `branch_cleanup_changes: skip — no diff data available`. Consequence: the one rule whose whole purpose is "branch-cleanup paired with no implementation change" withholds itself in exactly the case it now has evidence for, and says something false while doing it. This is the plan's own could-not-look-vs-nothing-to-look-at conflation, surviving in the rule whose two shapes D2's rationale analyses by name.
2. **`check-routing-decisions`' summary is not total over its checks** — `check-routing-decisions.py:774-778` counts only `pass` / `fail` / `skip`, while `evaluate_mis_prunes` can emit `inconclusive` (`:596-600`). Observed by running `cmd_run` on a plan with no decision log: two `inconclusive` checks and `summary {'passed': 0, 'failed': 0, 'skipped': 0}` — `sum(summary.values()) == 0` against `len(mis_prune_checks) == 2`. This is precisely the F4 defect the run fixed in the sibling file (`summarize_checks`, whose docstring forbids it) left unfixed in the file the run was editing. Pre-existing at `eb0124c^`, so not introduced here — but undeclared, and it is the same archetype as the deliverable.
3. **`filter_bookkeeping` seeds an optimistic default** — `check-manifest-consistency.py:276` sets `'diff_available': True` in the reduction block and relies on the single caller to overwrite it at `:728`. Today the one caller does; a second caller that forgot would silently assert evidence that does not exist, which is the failure `_withhold_on_absent_evidence` exists to prevent. Latent, not live.

Two further defects sit in the shipped standards document rather than in code, and are recorded here so every entry in `gaps.md` traces to a finding in this file (they were previously carried only in `gaps.md`, which was itself an n−1-of-n failure of this document):

4. **`standards/manifest-crosscheck.md` contradicts itself about the fragment shape** — the prose at `:120` names `diff_available` among the fields the `diff` block publishes, and `check-manifest-consistency.py:796` emits it on every success fragment, but the documented fragment example at `:139-153` stops at `majority_discarded`. The shape is the contract a renderer reads (G7).
5. **The LLM interpretation rule at `:180` states one of the two causes of `indeterminate`** — it says the status means "the rule saw only a minority of the supplied footprint", which is false for the `_withhold_on_absent_evidence` producer whose own message names no reduction at all. The same document states that second cause correctly at `:116`; only the rendering instruction restates one of them, and after G6 the no-evidence cause is the common one (G8).

No fail-open branch, guard-that-cannot-fire, off-by-one, or unguarded `None` was found in the delivered logic. `resolve_route_role` is order-independent by construction (it collects the matched role *set* then applies a fixed precedence), `classify_path`'s rung order matches its docstring, `classify_footprint` seeds every category so a zero is always explicit, and `summarize_checks` counts an unknown status under its own name so `sum(summary.values()) == len(checks)` holds unconditionally (verified by `test_every_check_is_counted_even_under_an_unknown_status`).

## Test adequacy

| Deliverable | Covering test(s) | Non-vacuity evidence |
|---|---|---|
| D1 (manifest site) | `test_multi_file_project_local_footprint_is_not_filtered`, `test_runtime_state_directory_is_still_bookkeeping` | red when `.claude/` is re-declared runtime state |
| D1 (routing site) | `test_routing_check_sees_project_local_production` | red under the same mutation |
| D1 (oracle API) | `TestReadBuildMapRoutes` / `TestResolveRouteRole` in `test_extension_base.py` (13 collected cases) | parametrized adverse-declaration-order arms exist for the precedence property |
| D2 | `test_majority_filtered_footprint_never_yields_a_bare_pass` + control `test_unreduced_footprint_still_passes_cleanly` | red when the downgrade is disabled (also takes `test_verdict_withheld_when_only_bookkeeping_changes` with it) |
| D3 | `test_m3_fires_on_canonical_verify_step_shape` + controls `test_m3_passes_when_the_diff_really_is_tests_only`, `test_m3_still_recognises_the_bare_module_tests_form` | red when the normalization is removed; the back-compat control stays green |
| D4 | `test_documented_relative_form_matches_the_absolute_form`, `test_manifest_check_also_resolves_the_relative_form`, `test_unresolvable_diff_file_fails_loudly` | red when the plan-dir candidate is dropped |
| CR-2 registry | `TestDiffFedRuleRegistryIsTheSingleSource` (4 tests) | `assert mod._DIFF_FED_RULES` precedes every relation — non-vacuous by construction |
| CR-6 non-vacuity | `test_dispatch_sets_are_subsets_of_the_category_vocabulary`, `test_every_status_the_script_emits_has_a_named_bucket` | both assert the population is non-empty *before* the subset relation (`:736-738`, `:803`) — the CR-6 fix is present as described |

No vacuous or tautological guard was found. Baseline: the four affected test files run **214 passed** on the current tree (re-measured twice under adversarial review; ~9–11 s, not the 23 s first recorded — wall-clock varies with machine load and is not evidence about the tree). Every mutation above was applied to a byte snapshot, run, and written back by hand; `git status --porcelain` is clean for all mutated files.

Coverage gap, not vacuity: nothing pins the routing check's `summary` against its own emitted statuses (defect 2 above). The manifest check has exactly that guard (`test_every_status_the_script_emits_has_a_named_bucket`); its sibling does not.

## Report accuracy

Claims re-derived and **true**: the population (2) and both denominators (427 / 428) with the added file named correctly; the oracle route `.claude/skills/*.py → production` and its emitter `_project_local_skill_globs()`; the post-fix reproduction figures (`files_filtered: 0, files_kept: 7`) and "there are six" project-local modules; `git ls-files .plan/` → **13** tracked paths (the A7 premise); "10 `.java` files and **zero** `*Spec.java`" — both exact; the `test_extension_base.py` figures (11 functions / 13 collected); all 25 cited guard names exist; the declared collateral (`test_verdict_withheld_when_only_bookkeeping_changes` no longer carries `.claude/settings.local.json` and expects `indeterminate`); the M1 skip-message doc correction (`manifest-crosscheck.md:156` matches the emitted string); the bridge claim (the merge commit's only `doc/plans/` changes are this plan's own `plan.md` rename and `report-01.md`); and the reviewer-participation table — PR #1288's stored review bodies show `sourcery-ai` refusing on the *"larger than the review limit of 150000 diff characters"* ceiling at head `8cd95a7`, `coderabbitai` posting **"Actionable comments posted: 6"** at head `622c052`, and the delivered head being `ad14fee`, exactly as described.

Claims that are **false against the tree**:

> "`test/plan-marshall/plan-retrospective/test_footprint_oracle_classification.py` carries **25 test functions, collecting as 25 cases** … Both figures re-derived against the delivered tree"

The delivered tree holds **31** functions collecting as **31** cases, at the delivering commit and now. (G4)

> "11 + 14 = 25, which reconciles with the collected count above."

The collected count is 31; the reconciliation is arithmetic over a superseded figure. (G5)

Unverifiable here (stated, not assumed): the `./pw verify` figures (`20695 passed, 14 skipped`, mypy 413/766 files) — re-running the full suite is out of scope for this audit; the red-first record (`10 failed, 1 passed`) — it describes a pre-fix tree that no longer exists on this branch; and the per-commit gate / trailer claims — the branch was squash-merged, so the six commits are not in this history.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| The `*Spec.java` survivor (exonerating for the routing consumer, bounded) | **Open, and inert here** | `TEST_NAME_RE` at `_footprint_classification.py:146-149` carries `[^/]+Spec\.java`; `git ls-files '*Spec.java'` → 0, `'*.java'` → 10. Cannot fire on this repository, exactly as declared |
| "The record's own defect class" — re-derive any count / guard name rather than trusting it | **Open, and it caught this report** | Every guard name held; the D5 count did not (G4/G5). The warning was correct about its own document |
| `_footprint_resolver.py`'s `.plan/` clause; sibling modules may carry the same blanket premise | **Open** | The file itself is fixed (`:173-178`). A sibling still carries it: `tools-file-ops/scripts/file_ops.py:270` — *"CI runners, fresh clones, and consumer installs have no `.plan/local` yet because `.plan/` is gitignored"* (G10) |
| The oracle itself is unconsolidated — this plan is one consumer | **Open by design** | `resolve_route_role` is a consumer-side lookup in `extension_base`; no consolidation was attempted, per the plan's Out of scope |
| Two more private copies of canonical-verify prefix knowledge, plus D3's third local normalizer | **Open, and the residue's own count is one short** | `manage-config/scripts/_cmd_quality_phases.py:68`; `tools-marketplace-inventory/scripts/_dep_detection.py:169`; `check-manifest-consistency.py:83`. An independent sweep found a **fourth**: `manage-execution-manifest/scripts/_manifest_core.py:324` `_CANONICAL_VERIFY_PREFIX = 'verify:'`, consumed at `:373-374` by `_role_of`, which performs the *same* `canonicalize_step_key`-then-strip-`verify:` normalization D3 added at `check-manifest-consistency.py:392-395` — i.e. the composer that emits the shape already carried the function the consumer re-implemented. A fifth partial copy is `_config_defaults.py:751` `_VERIFY_STEP_PREFIX = 'default:verify:'`. All agree behaviourally today (G11) |
| The delivered head `ad14fee` was never re-reviewed | **Open, and true in substance — the original evidence line was not** | The only two reviews carrying a *review body* are at heads `8cd95a7` (sourcery's size refusal) and `622c052` (coderabbit's "Actionable comments posted: 6"). ⚠ `get_reviews` does list **six further `coderabbitai[bot]` review records at `ad14fee` itself** (2026-08-18T01:47–01:48Z), so the audit's original "no bot review exists at `ad14fee`" was false as stated. Every one of those six is a bodyless `COMMENTED` record — the thread replies to the run's resolution comments — not a fresh review of the head, so the substantive claim (no reviewer has assessed the delivered head as a whole) stands, on corrected evidence |
| `sourcery-ai` never reviewed this diff (150k-char ceiling) | **Open, does not reopen** | Its stored review body states the ceiling verbatim |

## Out-of-scope and collateral

Nothing forbidden was built. The plan excluded (a) consolidating the oracle — the run added a *consumer-side* lookup to `extension_base` and left the build extensions' declarations untouched; (b) the auditor's other detector-integrity defects — `check-dispatch-audit.py` and the audit skill are untouched by `eb0124c`; (c) attribution of the project-local tree to a module — no `manage-architecture` or attribution surface appears in the diff. The unreachable rule moved here as the plan directed and was not re-added elsewhere.

Two collateral changes are declared in the report and both check out: the `manifest-crosscheck.md` M1 skip-message correction, and the renamed/retargeted `test_verdict_withheld_when_only_bookkeeping_changes`. I found no undeclared collateral in the merge commit's 15 files.

## Method and coverage

- Read `plan.md` and all 715 lines of `report-01.md`, then the shipped surfaces: `_footprint_classification.py`, `check-manifest-consistency.py`, `check-routing-decisions.py`, `_footprint_resolver.py`, `extension_base.py` (`route_matches`, `read_build_map_routes`, `resolve_route_role`, `_read_build_map_globs`), `standards/manifest-crosscheck.md`, `references/routing-decision-verification.md`, `plan-retrospective/SKILL.md`, plus the composer side (`_manifest_core.py`, `_manifest_decide.py`, `_step_key_canonical.py`) needed to judge D3.
- Re-derived every count at the moment of stating it, from `git ls-tree` / `git ls-files` / `grep -c` / `pytest --collect-only`, never from the report.
- Ran the scripts directly (importing them with the bundle script dirs on `sys.path`) for the D1 reproduction, the M4 empty-diff case, and the routing-summary case, because those verdicts depend on behaviour rather than on text.
- Mutation-tested four guards, one per deliverable D1-D4, each mutation reintroducing the specific defect its guard names. Snapshots were taken to `$TMPDIR/verify-320-mutsweep/` and written back by hand; no `git checkout`/`restore`/`stash` was used, and no file I did not mutate was touched. `git status --porcelain` is clean for all three.
- Verified the PR-side claims through the GitHub API (stored review bodies), not through check-run states.
- **Not checked:** the full `./pw verify` figures and its six coverage dimensions (out of scope for this audit, and the run's own tool output is the only record); the pre-fix red-first record (the tree it describes is gone); the per-commit gate and trailer claims (squash-merged); and the four verification rounds' internal accounting beyond the artifacts they produced.
