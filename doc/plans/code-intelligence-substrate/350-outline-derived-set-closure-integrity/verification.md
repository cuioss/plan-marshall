# Verification — 350-outline-derived-set-closure-integrity

**Audited:** `plan.md`, `report-01.md`, `report-02.md`, `actual-state.md`
**Tree state:** `9f8cc38` on `claude/code-intelligence-substrate-analysis-kah884` (the plan landed on
`main` as squash-merge `63943f5`, "fix(qgate): check the declared set for CLOSURE, not only for
existence (#1295)")
**Overall verdict:** CONFIRMED WITH GAPS

The shipped code does what D1–D4 asked for, and the guards that protect it are non-vacuous — seven
independent mutants were applied and every one went red at the guard that names it. The gaps are
almost entirely in the *records*: run 02's rebase silently dropped two of run 01's commits, so the
merged `report-01.md` carries a defect run 01 had already fixed and loses a build-gate result run 01
had already recorded — while `report-02.md` states that "every commit's tree is preserved". One
substantive coverage hole exists in the shipped closure itself (a declared glob in the write-set is
enforced by neither closure when it matches nothing yet).

## What run 02 changed relative to run 01

Run 01 (report-01.md) built D0–D5 and was halted by operator instruction before the PR cycle;
`actual-state.md` is its halt inventory. Run 02 (report-02.md) added **no deliverable of its own**.
Concretely, run 02:

| Change | Verified against the tree |
|---|---|
| Rebased run 01's commits onto `origin/main` and re-pushed as `claude/…-3i53aj`; opened PR #1295 | `origin/claude/derived-set-closure-integrity-g7n8x2` still exists with 11 commits above `eb0124c`; `…-3i53aj` no longer exists on `origin` (deleted at merge). **The rebase carried 9 of those 11 commits** — see § Report accuracy, the headline finding. |
| Ran verification round 4 (the last of run 01's declared 4-round budget) and fixed 15 condition-A findings (A1–A15) | A11–A13 confirmed fixed: `grep -rn "5+6+7\|5, 6, 7\|5 + 6 + 7" marketplace/ doc/ .claude/` returns **no** marketplace hit. A14 fixed at `authoring-guide.md:74`. A15 fixed at `request-result-alignment.md:34,35,41`. |
| Closed B1 and B2 (two round-4 mutation survivors) rather than characterising them | Both guards proven non-vacuous by mutation here — M5 and M6 below. |
| Fixed F-R1 (`cuioss-review-bot`): a raw `int(task["number"])` on the referrer-finding path | `_qgate_closure.py:383` now reads `_as_int(task.get('number')) or 0`; guarded by a 3-way parametrized test plus an absent-key test (`test_qgate_closure.py:892-941`). |
| Fixed F-CI1: a test whose precondition hard-coded the checkout's depth below `/` | `test_qgate_closure.py:556` derives the `..` count from `len(PROJECT_ROOT.resolve().parts) - 1`. |
| Declared the previously-undeclared collateral (the phase-4-plan step renumbering in three nav docs + the SVG) | The renumbering is present; the `Steps 5+6+7` sweep is clean. |
| Repaired two links in `280-…/report-01.md` broken by the plan-file move | Both resolve: `280-…/report-01.md:33,489` → `../350-…/plan.md`. Sweep for the pre-move path returns exactly one hit, report-02's own prose (re-derived). |
| Recorded the branch build gate at `117d351` and the CI `verify` result on the final head | Historical; not re-derivable from the tree (UNVERIFIABLE). |

Run 02 also **edited `report-01.md` and `actual-state.md` in place** (A1–A5, A7, A8). The audit below
treats the merged text of those files as the claim under test.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | GATE: confirm each defect at HEAD, mutating nothing | 5 confirmed, 1 refuted-in-part, all with file-and-symbol citations | Four of six citations spot-checked and all resolve at the sites named | CONFIRMED |
| D1 | Completeness is CLOSURE, not existence | `_qgate_closure.py` computes projection + referrer + claim-vs-index; wired as checks 7–8 | Present and wired; the "existence passes, closure fails" fixture is real and proven load-bearing | CONFIRMED (one coverage hole — G8) |
| D2 | Run the declared sweep before freezing the write-set | `check_declared_scope_reconciliation` compares a declared glob against the enumerated list | Present, mechanical, mutation-proven; the enabling parser/validator/recall widening is present | CONFIRMED (G8 lands on this check too, but D2's own *Done when* — the wide-scope/narrow-write-set pair — is met) |
| D3 | Assert `detector_population ⊇ fix_set_population` explicitly | Normative in `q-gate-validation.md` § 2.9a; discharged by a published `population` block flipping `ambiguous` | Both present; the positive-population guard asserts non-empty **and** names every known hit | CONFIRMED |
| D4 | A closure claim is a hint, never a licence | Closure lives in the unconditional Step 8, not the bypassable Step 8b | Structurally true; the adversarial test goes red when a bypass is injected (M7) | CONFIRMED |
| D5 | Tests each verified to fail pre-fix + characterization-corpus rule | 49 new test functions; corpus aligned, exclusions stated | Tests present and non-vacuous, but the counts are stale (54 today) and the **rule** was applied without being codified anywhere normative | PARTIAL |

## Per-deliverable detail

### D0 — GATE: confirm each defect at HEAD

- **Required (plan):** each defect carries a confirmed/refuted verdict with a file-and-symbol citation; mutates nothing.
- **Claimed (report):** six rows, five CONFIRMED (one "sharper than stated"), one REFUTED in part.
- **Found:**
  - "Existence, not closure" → `_cmd_qgate_mechanical.py:342` `_check_files_exist`, whose docstring at
    :349-364 documents exactly the intent-dependent predicate D0 describes (`write-replace` skipped,
    `read`/`delete` require existence, `write-new` inverted). `_check_coverage` (:176-224) relates
    deliverables to tasks by *reference count only*, never by path. ✔
  - "A closure claim can suppress downstream re-checking" → `phase-4-plan/SKILL.md:938`
    (`scope_estimate == surgical AND affected_files_count <= 2`) and :936-950. ✔
  - "A declared sweep wider than the write-set goes unreconciled" →
    `phase-3-outline/standards/outline-workflow-detail.md:811` § "Survey-scope vs mutation-scope
    declaration". ✔
  - "The routing decision's pre-override input is overwritten by its output" →
    `manage-status/scripts/_cmd_planning_lane.py:1004` writes `references['scope_estimate']`;
    `scope_provenance` is computed at :994, logged at :1019 and **never persisted**. ✔ (still true — R1)
- **Checks run:** direct reads of each cited symbol; `grep` for `scope_provenance` across all bundle scripts.
- **Verdict:** CONFIRMED. The two claims I did not independently re-derive are the "staged premise
  expires" convergence claim and the "one item already closed" refutation, both of which are
  restatements of citations verified above.

### D1 — outline completeness is CLOSURE, not existence

- **Required (plan):** a closure computation exists **and** a fixture in which every declared path
  resolves yet the set is incomplete is detected.
- **Claimed (report):** three closures in `_qgate_closure.py`, run as checks 7 and 8;
  `test_qgate_reports_closure_gap_while_files_exist_stays_clean` is the required fixture, made
  non-vacuous in round 1.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_qgate_closure.py:160`
    `compute_projection_gaps`, `:180` `compute_referrer_gaps`, `:425`
    `check_declared_scope_reconciliation`.
  - Wired at `_cmd_qgate_mechanical.py:674-697`; published as `checks['declared_set_closure']` and
    `checks['declared_scope_reconciliation']`.
  - The fixture: `test/plan-marshall/manage-tasks/test_qgate_closure.py:458`. Its steps carry `read`
    intent (`_task` default, :148) over two real repository files, so `files_exist` runs its
    existence predicate and passes on the merits; the closure still reports 1.
  - The anti-vacuity control: `test_qgate_closure.py:506`
    `test_files_exist_zero_is_load_bearing_not_vacuous` swaps in absent paths and asserts
    `files_exist == 1`.
- **Checks run:** `uv run python -m pytest test/plan-marshall/manage-tasks/test_qgate_closure.py -o addopts=""`
  → **38 passed**. Mutations M1, M2, M3, M4, M7 (see § Test adequacy) — all detected.
- **Verdict:** CONFIRMED. The *Done when* is met literally, and the fixture's `files_exist: 0` is a
  measurement rather than a skip. One coverage hole remains (G8): `compute_projection_gaps:177`
  deliberately excludes globs and delegates them to the reconciliation check, but the reconciliation
  check can only report *matches the deliverable does not enumerate* — so a glob in the write-set that
  matches **zero existing files** falls through both and reconciles clean with
  `population_complete: True`. It is a missing **projection obligation**, not a lying population: the
  block does publish `matches_enumerated: 0`; nothing asserts on it. ⛔ The fix must not be reached by
  making `compute_referrer_gaps` `fnmatch`-aware — that rule is deliberate and
  `test_referrer_reports_a_target_covered_only_by_a_glob` (re-mutated here, M1) pins it.

### D2 — run the declared sweep before freezing the write-set

- **Required (plan):** the `{declared scope wide, write-set narrow}` pair is detected mechanically, by
  comparing a declared glob against the enumerated file list; out-of-constraint hits enumerated and
  each resolved explicitly (widen with recorded authorisation, or narrow and document the exclusion).
- **Claimed (report):** `check_declared_scope_reconciliation` expands each declared glob (normalising
  first), enumerates including hits outside the declaration, emits one finding per glob **that matches
  files the deliverable does not also enumerate**, states the total and names a bounded prefix with
  `+N more`. Enabled by making the survey pair machine-visible.
- **Found:**
  - `_qgate_closure.py:425-550`. Normalisation at :247 (`posixpath.normpath`), escape rejection at
    :248, `~`/absolute rejection at :245, directory-only-as-unmeasured at :474-476, total + bounded
    prefix + `+N more` at :507-539, both resolutions named in the finding detail at :531-535.
  - Enabling widening: `_plan_parsing.py:405` `extract_survey_scope`, `:416` `extract_mutation_scope`,
    `:269-283` carried on every deliverable record, `:503` `deliverable_write_set` unions
    `mutation_scope`; `manage-solution-outline.py:359-370` accepts the survey pair as satisfying the
    section requirement; `check-artifact-consistency.py:185-189` reads all three headings.
  - Authoring rule: `outline-workflow-detail.md:826` § "⛔ The declared sweep is RUN before the
    write-set is frozen", carrying the ⚠ that a prose warning is not a control.
- **Checks run:** mutation M2 (hard-coded hit slice) → detected. Executed
  `validate_deliverable_contract` on a hand-built survey-scope deliverable: the survey pair satisfies
  the section requirement and produces no wildcard/intent error.
- **Verdict:** CONFIRMED.

### D3 — assert `detector_population ⊇ fix_set_population` explicitly

- **Required (plan):** the population assertion exists as a normative line, and carries a
  positive-population guard — the slice is non-empty **and** contains a known hit.
- **Claimed (report):** stated in `q-gate-validation.md` § 2.9a; discharged by a published
  `population` block that flips `ambiguous`; `scanned_paths` publishes member identities.
- **Found:**
  - The normative blockquote in
    `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md` § 2.9a
    ("Declared-Set Closure (mechanical, unsuppressible)", heading at `:392`) — the exact line
    `detector_population ⊇ fix_set_population` is at **`:407`**, under the "Normative population
    assertion" lead-in at `:405`.
  - Mechanism: `_qgate_closure.py:411-421` and `:541-549` return `population`;
    `_cmd_qgate_mechanical.py:721-728` publishes `population` / `population_complete` and computes
    `ambiguous = not parseable or not population_complete`.
  - Member identities: `_qgate_closure.py:418` `scanned_paths`, capped at :80 with
    `scanned_paths_truncated` disclosing the cap.
  - Positive-population guard: `test_qgate_closure.py:303`
    `test_declared_glob_wider_than_the_enumeration_is_reported` asserts `expected_hits` non-empty
    (:311) **and** that every known hit appears in the finding (:322-323). The expectation is derived
    by an independent oracle (`_independent_expansion`, :97 — a tree walk plus `fnmatch`, not
    `Path.glob`), with its two fidelity bounds stated at :109-117.
- **Checks run:** mutation M3 (`population_complete` hard-coded True) → 2 tests red, including the
  end-to-end `ambiguous` propagation. Mutation M4 (drop the `~` guard) → detected.
- **Verdict:** CONFIRMED.

### D4 — a closure claim is a hint, never a licence

- **Required (plan):** a downstream re-check runs regardless of an upstream closure assertion,
  verified adversarially — assert the closure claim and confirm the check still runs.
- **Claimed (report):** structural — the closure checks live in phase-4-plan Step 8 (unconditional
  inline script), not Step 8b (the dispatched validator B2 suppresses); the normative line is added at
  the B2 predicate itself.
- **Found:**
  - `_cmd_qgate_mechanical.py:32-37` (module docstring: "These closure checks run unconditionally, and
    that is load-bearing"); the call sites at :674-675 sit on the unconditional path with no predicate.
  - `phase-4-plan/SKILL.md:932` states the self-reinforcing property explicitly and names exactly what
    B2 suppresses (`module-mapping-validator` / `scope-criterion-validator`), correcting round 1's
    invented rationale.
  - `q-gate-validation.md:403` ("Their placement is the point, not an implementation detail").
  - The adversarial test: `test_qgate_closure.py:834`
    `test_closure_check_runs_under_the_surgical_scope_bypass_shape` — writes `references.json` with
    `scope_estimate: surgical`, asserts **both** conjuncts as preconditions (:864 and :885, the second
    re-derived through the same parser phase-4-plan uses), then asserts the closure still fires.
- **Checks run:** mutation **M7** — I injected a bypass into `cmd_qgate_mechanical` keyed on the
  presence of `references.json` (i.e. a closure claim licensing a skip). Result: `1 failed, 37 passed`,
  the single failure being `test_closure_check_runs_under_the_surgical_scope_bypass_shape`. The
  adversarial guard is load-bearing, not decorative.
- **Verdict:** CONFIRMED.

### D5 — tests, each verified to fail pre-fix, plus the characterization-corpus rule

- **Required (plan):** tests each verified to fail pre-fix, **plus** a characterization-corpus rule —
  a fixture corpus is population-derived from the live corpus directory: enumerate every fixture, then
  justify each *exclusion* explicitly; opt-out with a stated reason, never opt-in by selection.
- **Claimed (report):** "**49** new test functions across five modules", re-derived with
  `grep -c '^def test_'`; red-before-green by mutation, not by stash; the corpus was **aligned, not
  exempted**, with three stated exclusions; `_ALL_CHECKS` cross-checked against the live key set.
- **Found:**
  - Test-function counts re-derived at the moment of this claim with `grep -c '^def test_'`:

    | Module | Now | Pre-merge (`63943f5^`) | New |
    |---|---|---|---|
    | `test/plan-marshall/manage-tasks/test_qgate_closure.py` | 36 | — (new file) | 36 |
    | `test/plan-marshall/manage-solution-outline/test_survey_scope_declaration.py` | 10 | — (new file) | 10 |
    | `test/plan-marshall/plan-retrospective/test_recall_survey_scope.py` | 5 | — (new file) | 5 |
    | `test/plan-marshall/manage-solution-outline/test_foreign_deliverable_column.py` | 12 | 11 | 1 |
    | `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py` | 15 | 13 | 2 |
    | **Total** | | | **54** |

    Report-01 says 34 / 8 / 4 / 1 / 2 = **49**. Three of the five figures are stale and the total is
    wrong by five. No later commit touched these files
    (`git log --oneline 63943f5..HEAD -- <the three new files>` is empty), so the drift is internal to
    the run's own record — see G5.
  - Corpus alignment: `test_manage_tasks_qgate_mechanical.py:28-35` (`_EXISTING_FILE` used as both the
    declared path and the step target), `:42-51` `_ALL_CHECKS`, and the live-key cross-check at `:196`
    (`assert set(result['checks']) == set(_ALL_CHECKS)`).
  - Stated exclusions: the three `(read)` declarations at `:213`, `:661`, `:701` — exactly the three
    fixtures report-01's exclusion table names — plus the `_MISSING_FILE` fixture at `:419/:426` and
    the verification-profile carve-out pinned by
    `test_qgate_closure.py:415 test_verification_tasks_are_excluded_from_the_scanned_population`.
  - **The rule itself is nowhere normative.** `grep -rn "characterization" marketplace/bundles --include=*.md -il`
    returns one unrelated file (`manage-solution-outline/examples/refactoring.md`); nothing in any
    skill or standard states the population-derived-corpus rule. It survives only as a rationale
    comment in one test module (`test_manage_tasks_qgate_mechanical.py:28-34`) and as prose in
    `report-01.md`, which is a record, not a control — the exact "prose warnings are NOT a control"
    failure the plan's own § "sub-classes" names.
- **Checks run:** the counts above; the seven mutations in § Test adequacy; full run of the three new
  suites (53 passed).
- **Verdict:** PARTIAL. The test half is discharged and verified non-vacuous. The
  characterization-corpus half was *applied* to this one corpus but not *codified*, so nothing carries
  it to the next corpus — and the deliverable's own accompanying count is stale.

## Correctness review

I read `_qgate_closure.py` end to end, the closure call site in `_cmd_qgate_mechanical.py:600-744`,
`_plan_parsing.py`'s three extractors and `deliverable_write_set`, `check-artifact-consistency.py`'s
`_extract_bullet_entries` / `extract_modification_intent_files`, `manage-solution-outline.py`'s
`validate_deliverable_contract` check 3, and `foreign_pr_gate.py::_foreign_paths_by_deliverable`.

**No fail-open was found on the closure path itself.** Every unmeasurable condition the module can
meet — an absolute pattern, a home-relative pattern, a repo-escaping pattern, a matcher exception, a
directory-only match, an expansion stopped at the ceiling, a task naming an absent deliverable —
resolves to *unmeasured* rather than *clean*, and each flips `population_complete` and therefore
`ambiguous`. `expand_declared_glob`'s exception handler (`:262`) returns `expandable=False`, which is
the conservative direction.

Three real defects:

1. **A declared glob in the write-set is enforced by neither closure when it matches nothing yet.**
   `_qgate_closure.py:177` excludes patterns from the projection closure and delegates them to the
   reconciliation check; `:504` reports only *matches the deliverable does not enumerate*. A
   deliverable declaring `**Files expected to mutate:** - src/newthing/*.py` — a write-new surface,
   which the validator accepts because check 3a's wildcard rejection walks `affected_files` only
   (`manage-solution-outline.py:372-377`) — therefore produces:

   ```
   closure gaps: []  | pop_complete: True  | declared_paths_scanned: 2
   recon  gaps: []  | globs_declared: 1, globs_expanded: 1, matches_enumerated: 0,
                      directories_matched: 0, population_complete: True
   ```

   (executed against the live tree, with one task whose single step targets a path the deliverable
   *does* declare, so the referrer closure has nothing to say). **Control, executed in the same
   probe:** replace the pattern with the literal `src/newthing/thing.py` and the projection closure
   fires — `declared_set_closure: deliverable 1 declares 'src/newthing/thing.py' as a write but no
   task targets it`. The glob spelling is the sole cause.

   ⚠ **Stated precisely, because the first version of this row overstated it:** the population is not
   dishonest — `matches_enumerated: 0` is published, which is exactly the distinction
   `q-gate-validation.md:407` says the published count carries. What is missing is the **projection
   obligation**: nothing asserts on that zero, so a clean `total_failed` is returned over a declared
   write scope no task was ever required to cover. Consequence: the one deliverable shape whose
   mutation set is least knowable at authoring time is also the one no closure constrains. → **G8**.

2. **`deliverable_write_set`'s dedupe is byte-exact, so its docstring claim is false for a spelling
   variant.** `_plan_parsing.py:510` compares raw strings while `_qgate_closure.normalize_declared_path`
   exists precisely because `./x/y.py` and `x/y.py` name the same file. Executed:
   `{'affected_files': [{'path': './src/a.py', …}], 'mutation_scope': [{'path': 'src/a.py', …}]}` →
   `['./src/a.py', 'src/a.py']`, two members, against a docstring (`:479`) promising one. The closure
   re-normalises so its own verdict is unaffected; every other `deliverable_write_set` consumer sees
   the duplicate. → **G16**.

3. **`phase-4-plan/SKILL.md:1047` contradicts the same file's § Step 8b.** It states
   `qgate_validation_required` is "`true` on every successful phase-4-plan completion (Step 8b signals
   unconditionally …) and `false` **only on the unrecoverable error path**", while :936-950 defines two
   further paths to `false` (the B1 knob and the B2 surgical bypass) and :61 — a line **this diff
   edited** — names both. Pre-existing on `origin/main` (verified with `git show 63943f5^:…`), but it
   is the n−1 site of the exact claim D4 is about, inside a file the change edited. → **G9**.

Checked and found clean, recorded so the negative is not re-derived:

- **The keyword-drift haystack** (`_cmd_qgate_mechanical.py:479`) reads `affected_files` only, which
  looked like a missed widening. It is not: the haystack also appends the deliverable's whole prose
  body (`:486-487`, sourced from `block['content']` at `:154`), and the survey/mutation bullets live in
  that body verbatim. The mutation surface reaches the haystack.
- **`scope_creep_check.py:69`** reads `references.affected_files` **plus** every `TASK-*.json` step
  target, so the mutation surface reaches the denominator through the task targets — as report-02's
  own "checked and found clean" note states.
- **`_check_coverage`** already catches the deliverable-with-no-tasks case, so the glob hole in (1)
  above is not reachable through a task-less deliverable; it needs a deliverable that has tasks and
  whose write surface is glob-only.

## Test adequacy

Coverage map, all paths re-derived:

| Deliverable | Guarding tests |
|---|---|
| D1 projection | `test_qgate_closure.py:190, 200, 208, 224, 283` |
| D1 referrer | `test_qgate_closure.py:245, 254, 261` |
| D1 end-to-end + non-vacuity | `test_qgate_closure.py:458, 482, 506` |
| D2 claim-vs-index | `test_qgate_closure.py:303, 326, 340, 352, 373, 531, 573, 596, 629, 653, 680` |
| D3 population | `test_qgate_closure.py:390, 401, 415, 715, 730, 779, 810` |
| D4 adversarial | `test_qgate_closure.py:834` |
| Survey-pair parsing / validation | `test_survey_scope_declaration.py` (10 functions) |
| Recall extractor | `test_recall_survey_scope.py` (5 functions) |
| Foreign column / phase-6 landing gate | `test_foreign_deliverable_column.py:+1`, `test_foreign_pr_gate.py:+2` |
| Corpus alignment / live-key cross-check | `test_manage_tasks_qgate_mechanical.py:162-198` |

**Mutation sweep run by this audit.** Each mutation was applied by writing back a byte snapshot taken
into `$TMPDIR/verify-350-mutsweep/` by a harness I wrote (`shutil.copy2` + verbatim restore); no
`git checkout` / `git restore` / `git stash` was used, and `git status --porcelain` was confirmed empty
for each mutated file after restore.

| # | File | Mutation | Result |
|---|---|---|---|
| M1 | `_qgate_closure.py:196` | referrer closure accepts a target a declared glob would `fnmatch` | **DETECTED** — 1 failed (`test_referrer_reports_a_target_covered_only_by_a_glob`), 37 passed |
| M2 | `_qgate_closure.py:507` | `unenumerated[:_MAX_HITS_NAMED]` → `unenumerated[:1]` | **DETECTED** — 1 failed (`test_the_finding_names_every_hit_and_states_the_true_total`), 37 passed |
| M3 | `_qgate_closure.py:420` | `population_complete: not unmapped_tasks` → `True` | **DETECTED** — 2 failed (population + end-to-end `ambiguous`), 36 passed |
| M4 | `_qgate_closure.py:245` | drop the `~` half of the expandability guard | **DETECTED** — 1 failed (`test_a_home_relative_glob_is_unmeasured_not_empty`), 37 passed |
| M5 | `check-artifact-consistency.py:295` | `intent or default_intent` → `default_intent or intent` (B1's defect) | **DETECTED** — 1 failed (`test_an_explicitly_marked_survey_bullet_reaches_the_recall_denominator`), 963 passed |
| M6 | `_plan_parsing.py:510` | drop the `seen` dedupe (B2's defect) | **DETECTED** — 2 failed, 189 passed |
| M7 | `_cmd_qgate_mechanical.py:674` | inject a bypass so an upstream artifact licenses skipping the closure (D4's adversarial property) | **DETECTED** — 1 failed (`test_closure_check_runs_under_the_surgical_scope_bypass_shape`), 37 passed |
| M8 | `foreign_pr_gate.py:205` | narrow the foreign-path scan back to `affected_files` | **DETECTED** — 2 failed, 13 passed |

No vacuous guard was found. The two guards report-02 added late (B1, B2) are genuinely load-bearing —
M5 and M6 both reach the opposite verdict, not merely a shorter list.

**Adversarial re-run of this sweep.** M1, M3, M5, M7 and M8 were re-applied independently (same
snapshot-and-restore discipline, `$TMPDIR/adv-350-…/snapshots`, no `git checkout` / `restore` /
`stash`) and every failure count above reproduced verbatim: M1 `1 failed, 37 passed`; M3 `2 failed,
36 passed`; M5 `1 failed, 963 passed`; M7 `1 failed, 37 passed`; M8 `2 failed, 13 passed`, with the
same named tests failing. One further mutant, devised for this review rather than taken from the
table, was applied to close a gap in the sweep's own coverage:

| # | File | Mutation | Result |
|---|---|---|---|
| M9 | `_cmd_qgate_mechanical.py:383` | widen the `files_exist` skip from `write-replace` to `write-replace` **and** `read` — the exact pre-round-1 shape that made D1's fixture vacuous | **DETECTED** — 1 failed (`test_files_exist_zero_is_load_bearing_not_vacuous`), 37 passed |

M9 matters because D1's whole *Done when* rests on `files_exist: 0` being a measurement rather than a
skip, and the audit had verified that by reading the fixture rather than by attacking the production
predicate it depends on. It holds. `git status --porcelain` was empty for every mutated file after
restore, and no production file is modified at the close of this review.

**One live-directory precondition remains**, as report-02 disclosed (B4):
`test_qgate_closure.py:696` asserts `len(hits) <= _closure._MAX_HITS_NAMED` where `hits` is the live
`manage-tasks/scripts/*.py` set. Re-derived: 14 scripts today against a cap of 20, and the comparison
is `<=`, so **seven** additions (14 → 21) turn an unrelated change into a hard failure — `report-02.md`
had this figure right and an earlier version of this row said six. Still open — **G11**.

## Report accuracy

### ⛔ The headline finding — run 02's rebase dropped two of run 01's commits, and reported the recovery as complete

`report-02.md:19-36` states run 01 "committed and pushed **nine** commits", that those "nine commits
were **rebased** onto current `origin/main` and re-pushed", and that "the rebase was conflict-free, and
**every commit's tree is preserved**".

Re-derived: `git log --oneline eb0124c..origin/claude/derived-set-closure-integrity-g7n8x2 | wc -l`
→ **11** (and `git merge-base origin/main …g7n8x2` confirms `eb0124c` is the base). Only the first
nine (up to `ce4292c`) reached the branch that became PR #1295; the last two did not:

| Dropped commit | What it fixed | State of the merged tree |
|---|---|---|
| `f614b9a` "docs(plans): record the final clean verify result" | Replaced report-01 § Final gate's "_pending a clean re-run_" with the recorded clean gate (`=== verify: SUCCESS ===`, `20840 passed, 14 skipped in 385.92s`, run at `0f10d16` with nothing else touching the tree) and updated `actual-state.md` § 7 to match | `report-01.md:331` still reads "**Final gate** — _pending a clean re-run._" |
| `33392fd` "docs(plans): correct the report header and the stale commit enumeration" | Replaced "D1–D5 land across **four** commits" with a named list of **five** deliverable-bearing commits, adding the round-3 fix the count omitted | `report-01.md:73` still reads "D1–D5 land across four commits: …, and the round-2 fix commit" — the round-3 fix is still missing |

Proof: `git show ce4292c:…/report-01.md` diffed against the merged `report-01.md` differs only in the
rewritten SHAs (`a583652` → `51829af`, `d9f9534` → `3b57b7e`, …), in run 02's own round-4 edits
(A1/A2/A3/A7/A8) and in the header block run 02 added — **not one hunk of `f614b9a` or `33392fd`
appears**. The merged document is `ce4292c`'s text plus run 02's, with the two later run-01 commits
missing from both.

⚠ **What is established is the effect, not the mechanism, and this document does not assert one.**
`git log --date=iso-strict` puts `f614b9a` at `10:59:37` and `33392fd` at `11:00:00` UTC, and run 02's
first commit `d898934` at `11:03:13` — three minutes later. A rebase that dropped them and a fetch
taken before run 01's last push are equally consistent with the tree, and neither is recoverable now
that `…-3i53aj` is deleted. The claim under test is `report-02.md`'s, and it is false either way:
run 01 pushed eleven commits, not nine, and two of their trees are not preserved.

⛔ **Bound on the damage.** `git show --stat` on both commits: `f614b9a` touches `report-01.md` and
`actual-state.md`; `33392fd` touches `report-01.md`. **No production script and no test was lost** —
the loss is entirely in the record, which is why G1–G4 are report-defects and not code gaps.

Consequences, each a false statement standing in the landed tree:

1. `report-02.md` § "How run 01's work was recovered" — "nine commits" (11) and "every commit's tree is
   preserved" (two were not). → **G1**
2. `report-01.md:73` carries a count run 01 had *already* determined to be wrong and had already fixed.
   The paragraph's own ⚠ says "an earlier version of this line attributed all five deliverables to the
   first commit" — the later correction, which the same commit's message calls out as "wrong twice",
   is the one that was lost. → **G2**
3. `report-01.md:331-338` still promises "The gate is re-run once no other process is touching the
   tree, and the result recorded **here**". It was re-run, and the result was recorded there, and the
   record was destroyed. → **G3**
4. `actual-state.md:168-170` (written by run 02 as fix A5) asserts "Run 01 recorded **no** final gate —
   its § Final gate says 'pending a clean re-run'". Run 01 did record one; run 02's own rebase is why
   it is not there. → **G4**

This is proposal 1 in `report-02.md` § "What have we learned" materialising one level worse than
proposed: the run correctly foresaw that a rebase falsifies quoted SHAs, and did not notice that its
rebase had also dropped content.

### Other claims

| Claim | Verdict |
|---|---|
| `report-01.md:184-192` — 34 / 8 / 4 tests, "**49** new test functions" | **FALSE now, but true when run 01 wrote it.** Re-derived at HEAD: 36 / 10 / 5 / 1 / 2 = **54**. Re-derived at run 01's own tip (`origin/…-g7n8x2`): **34 / 8 / 4**, foreign-column 12 (from 11), pr-gate 15 (from 13) — all five figures exact there. Run 02's own commits added the five that falsify them (B1's guard, B2's two guards, F-R1's parametrized guard + absent-key case). No commit after the merge touched those files. → G5 |
| `report-02.md:242-246` (F-R1 sweep) — "The identical raw pattern appears at **six** sites in `_cmd_qgate_mechanical.py`" | **Not reproducible, and larger than either count.** Re-derived, `int(…['number'])` appears at :154, :184, :296, :300, :309, :310, :311, :502 (**8**), plus **five** raw reads fed to a `:03d` format — :213 and :215 (inline), :243 and :371 (assigned, formatted downstream) and :532 (inline) — **13** read sites. An earlier version of this row named only :243 and :371 and undercounted at 10. No reading of the file yields 6. → G6 |
| `report-02.md:569` (R3) — "re-derived … it is **13**" | **TRUE.** Re-derived exactly 13 sites naming phase-4-plan Step 8b as the manifest composer (enumerated in `gaps.md` G13). |
| `report-02.md:82-85` (Bridge) — the pre-move-path sweep "returns exactly **one** hit … the sentence above this one" | **TRUE.** `grep -rn '350-outline-derived-set-closure-integrity\.md' --include=*.md .` returns exactly that one line. |
| `report-02.md:346-348` — the reviewer registry returns three `author_login`s, M = 3 | **TRUE.** `coderabbit.md:36`, `pr-agent.md:58`, `sourcery.md:29`. |
| `report-02.md:94-96` / `report-01.md:299` — "8 production scripts and 9 test modules" | **TRUE.** `git show 63943f5 --name-only \| grep '\.py$'` → 8 production, 9 test. |
| `report-02.md:286` (B4) — cap 20, "14 today" | **TRUE.** `manage-tasks/scripts/*.py` → 14. |
| `actual-state.md:69` — "37 files changed, +2831/−250, across 8 commits" | **True as authored, stale now.** `git diff --shortstat eb0124c 0f10d16` → exactly 37 / +2831 / −250, and 8 commits — the state immediately before `actual-state.md` was written. At run 01's real head it is 38 / +3027 / −250 across 11. The document's banner scopes it to the halt, so this is disclosure-adequate. |
| Every commit SHA quoted in all three documents (`3b57b7e`, `9d257dd`, `4ec39fd`, `51829af`, `4f7ab38`, `f11e8b7`, `8486214`, `117d351`, `f2a7cd9`, `501ce21`, `d898934`) | **Unresolvable.** `git cat-file -t` reports MISSING for all eleven — branch `claude/…-3i53aj` was deleted at merge and the PR was squashed to `63943f5`. → G19 |
| `report-01.md` D5's mutant tallies (27 / 32 / 19-17-2) and all `./pw` output figures | **UNVERIFIABLE** — historical measurements of a tree state that no longer exists. Not re-derivable; not asserted false. |
| `report-02.md` § Reviewer participation bodies, CI run IDs, PR timeline | **UNVERIFIABLE** — no network access from this audit. The merge itself is confirmed (`63943f5` on `main`). |

### Plan clauses dispositioned by the run

`report-01.md:275-286` records that the plan's Verification bullet *"Each fixture carries the pre-fix
text verbatim for the predicate axis"* is **not satisfied as literally written**, and substitutes the
mutation campaign. That disposition is honest and the substitute is stronger for a set-computation
detector. Recorded here as a labelled deviation rather than a silent one — **G18**, low.

`report-01.md:288-295` records the expected-surface HYPOTHESIS `consumer-sweep.md` as **REFUTED**.
Confirmed: that file appears in no line of `git show 63943f5 --name-only`.

The plan's **third** expected-surface entry —
`plan-retrospective/scripts/check-artifact-consistency.py`, labelled HYPOTHESIS, "the recall check that
cannot see a path absent from every write-set" — is dispositioned by neither run report explicitly, and
an earlier version of this document left it unmentioned too. **Confirmed as the surface it was
hypothesised to be:** the file is in the diff (`git show 63943f5 --name-only`), its
`_extract_bullet_entries` was widened to read all three headings (`:185-189`, `:295`), and the widening
is guarded by `test_recall_survey_scope.py` (5 functions) and re-mutated here as M5. No gap — the
hypothesis was confirmed by the work, only never written down as confirmed.

## Declared residue — current status

| Residue item (from the reports) | Still open? | Evidence |
|---|---|---|
| **R1** — `scope_provenance` logged but never persisted; the router's own S2 input is overwritten by its output | **OPEN** | `_cmd_planning_lane.py:1004` writes only `references['scope_estimate']`; `scope_provenance` is computed at :994 and used only in the log line at :1019. `grep -rn scope_provenance` across all bundle scripts finds no persistence site. → G12 |
| **R2** — a `disabled` plan's footprint is derivable but reported unresolvable | **OPEN, deliberately unscoped** | 280 implemented, measured and reverted it; nothing in this diff touches `manage-references`, the composer or `extension_base`. Not re-scoped here. |
| **R3** — sites naming phase-4-plan **Step 8b** as the execution-manifest composer; canonical is **Step 7b** | **OPEN — exactly 13** | Enumerated in `gaps.md` G13. `phase-4-plan/SKILL.md:61` is correct (7b composes, 8b is the LLM Q-Gate), which makes the other 13 false. → G13 |
| **R4** — survey-pair disjointness is an authoring rule no check enforces | **OPEN** | `validate_deliverable_contract` (`manage-solution-outline.py:335-397`) never compares `survey_scope` against `mutation_scope`; the only mention of disjointness in the scripts is the defensive comment at `_plan_parsing.py:477`. → G14 |
| **R5** — `references.affected_files` does not carry the survey pair | **OPEN, with four consumers** | The under-filled field is read by `_cmd_classification_validate.py:128`, `_cmd_sibling_collision.py:125`, `manage-metrics.py:2630` and `scope_creep_check.py:69`; `phase-4-plan/SKILL.md:688` carries the ⚠ but the writer is unchanged. → G15 |
| **B3** — `manage-lessons` does not read the survey pair | **OPEN** | `manage-lessons/scripts/_lessons_query.py:155` — `for entry in deliverable.get('affected_files', [])`, nothing else. → G10 |
| **B4** — a live-directory precondition in `test_qgate_closure.py` | **OPEN** | `test_qgate_closure.py:696`; 14 scripts against a cap of 20. → G11 |
| **New (run 02)** — raw `int(x['number'])` conversions in `_cmd_qgate_mechanical.py` | **OPEN, and larger than reported** | 8 `int(…)` conversions plus 2 bare `:03d` formats, enumerated in G7/G6. The same crash-on-the-reporting-path shape F-R1 named. → G7 |
| **New (run 02)** — `250-…/report-01.md:100` restates the pre-widening coverage rule | **OPEN, deliberately** | Correct call: it is another plan's dated run record, not a live specification. No action. |
| **B1, B2** | **CLOSED** | Both proven non-vacuous here by M5 and M6. |
| **F-R1, F-CI1** | **CLOSED** | `_qgate_closure.py:383` guarded; `test_qgate_closure.py:556` derives the depth. |

## Out-of-scope and collateral

- **Arm B's items** (worktree-state discriminator, write-set-derived bucket, keyword-drift haystack):
  **respected**. The keyword-drift haystack builder (`_cmd_qgate_mechanical.py:465-488`) is unchanged
  except for a step-number reference in a docstring; `test_write_set_derived_classification.py`'s only
  edit is a five-line docstring pointing at the new sibling suite;
  `_cmd_planning_lane.py` is untouched by the diff.
- **The task-artifact emission defect**, **the plan-efficiency calibration table**, **moving the
  worktree creation point**: none appears in `git show 63943f5 --name-only`.
- **Declared collateral**: the phase-4-plan step renumbering across `call-graph.md`,
  `task-creation-flow.md` and `call-graph.svg`, disclosed in `report-02.md:575-594`. Verified present
  and consistent (the `5+6+7` sweep is clean).
- **Cross-plan write**: two link repairs in `280-…/report-01.md`, disclosed and correct.
- **Undisclosed collateral found by this audit**: none.

## Method and coverage

**Checked.** Read `plan.md`, `report-01.md`, `report-02.md`, `actual-state.md` in full; read
`_qgate_closure.py` (551 lines) in full and `_cmd_qgate_mechanical.py`'s check functions and command
body; read `_plan_parsing.py` in full; read the survey-pair sections of
`outline-workflow-detail.md`, `q-gate-validation.md` § 2.9a, `phase-4-plan/SKILL.md` § Step 6 / Step 8 /
Step 8b, `authoring-guide.md:74`, `request-result-alignment.md:34,35,41`; read `test_qgate_closure.py` in full and
the corpus headers of `test_manage_tasks_qgate_mechanical.py`. Ran the three new suites (53 passed) and
the `plan-retrospective` (964) and `manage-solution-outline` (191) suites under mutation. Executed
eight mutations, all detected. Executed three ad-hoc probes against the live tree (the glob-only
write-set case, the validator's treatment of a glob in `mutation_scope`, and the write-set dedupe under
spelling variance). Re-derived every count stated above at the moment of stating it, including the
run-01 branch's commit count and diffstat from `origin/claude/derived-set-closure-integrity-g7n8x2`.

**Search-negative controls.** Before believing the `5+6+7` sweep's empty marketplace result, the same
grep was confirmed to return hits elsewhere (the recipe skill's aspect numbering and this plan's own
report prose). Before believing "no normative characterization-corpus rule exists", the same grep
pattern was confirmed to match `manage-solution-outline/examples/refactoring.md`.

**Not checked, and why.**

- Every figure produced by a `./pw` run (source-file counts, pytest totals, timings) and every
  reviewer/CI interaction: historical measurements of a tree and a PR state this audit cannot
  reproduce. Recorded UNVERIFIABLE, never assumed true.
- The full `./pw verify` suite was not run — out of scope per the audit brief; the targeted suites were
  run instead.
- Two of D0's six rows (the "staged premise expires" convergence and the "one item already closed"
  refutation) were not independently re-derived; both restate citations verified elsewhere.
- No network access, so PR #1295's comment bodies and check-run history could not be read. The merge
  itself is confirmed from `git log` (`63943f5`).

**Tree hygiene.** Every mutation was restored from a byte snapshot under
`$TMPDIR/verify-350-mutsweep/`; `git status --porcelain` was verified clean for each mutated file
afterwards. A concurrently-running audit agent's own modification to
`platform-runtime/scripts/claude_runtime.py` was observed mid-sweep and deliberately left untouched;
it was gone by the end of this audit. No file outside this plan's directory was written.
