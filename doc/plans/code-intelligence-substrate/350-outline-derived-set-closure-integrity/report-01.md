# Run report — 350-outline-derived-set-closure-integrity (run 01)

**Date (UTC):** 2026-08-18    **Branch:** `claude/derived-set-closure-integrity-g7n8x2` (harness-assigned)
**PR:** _pending_    **Outcome:** _in progress_

## Verification round budget — declared before the first dispatch

**4 rounds.** The plan states no budget, so the run declares one, up front, before it knows what any
round will say. Exhausting it is a STOP CONDITION whose autonomous fallback is the contract's: every
finding condition **A** forbids leaving open is fixed regardless of the budget, and every surviving
**B** finding is characterised and disclosed per instance.

## Skills loaded

| Skill | Route | Why |
|---|---|---|
| `cloud-plan-lane` | plugin (`.claude/skills/`) | The run contract; loaded first, before reading the plan. |
| `plan-marshall:ref-code-quality` | bundle path | Always. |
| `pm-plugin-development:plugin-script-architecture` | bundle path | Always. |
| `plan-marshall:persona-implementer` | bundle path | The surface is production code. |
| `pm-dev-python:python-core` | bundle path | The surface is Python production code. |
| `pm-dev-python:pytest-testing` | bundle path | The surface includes Python tests. |

`pm-plugin-development:plugin-architecture` and `pm-documents:ref-asciidoc` were **not** loaded: no
bundle was structurally added or removed and no `.adoc` file was touched. The `SKILL.md` and standards
edits are corrections to specifications this diff made stale, not authoring of new skill structure.
No skill was unobtainable by either route.

## D0 — the gate

The plan required D0 to confirm each defect at HEAD with a file-and-symbol citation, and warned to
**expect closed items**. **D0 mutated nothing.** Every verdict below was read from the tree at HEAD.

| Claim (plan's label) | Verdict | Site |
|---|---|---|
| Completeness is checked by existence rather than closure (**OBSERVED**) | **CONFIRMED** | `_cmd_qgate_mechanical._check_files_exist` applies an intent-dependent existence predicate to each task STEP TARGET — requiring existence for `read` and `delete`, forbidding it for `write-new`, and skipping `write-replace` entirely. That is the whole of it: nothing in the mechanical pass compares the declared SET against anything. `_check_coverage` relates deliverables to tasks by *reference* (≥1 task per deliverable), never by path. |
| A closure claim can suppress downstream re-checking (**OBSERVED, first-party**) | **CONFIRMED, and sharper than stated** | `phase-4-plan/SKILL.md` § Step 8b **B2**: `scope_estimate == surgical AND affected_files_count <= 2` sets `qgate_validation_required: false`, skipping the whole dispatched q-gate-validation. ⚠ **Corrected in round 1:** an earlier version of this row named § 2.9 `consumer_sweep_completeness` and § 2.8's deletion-consumer sweep as the suppressed checks. They are not — `planning-outline.md` activates only `module-mapping-validator` and `scope-criterion-validator` at the phase-4-plan call site, and those two activate at phase-3-outline under a different guard. What B2 suppresses is the pair that reconciles LLM-authored task and deliverable shape against **live ground truth** rather than against the outline's own assertions. `affected_files_count` is *the cardinality of the outline's own declaration*, so the bypass is driven by the claim under question and is self-reinforcing: the more an outline under-enumerates, the likelier it skips the check that would find the omission. |
| A declared sweep wider than the listed write-set goes unreconciled (**OBSERVED**) | **CONFIRMED** | `outline-workflow-detail.md` § "Survey-scope vs mutation-scope declaration". The `survey_vs_mutation_scope_declared` check asserts BOTH fields are **present** — a presence check, not a reconciliation. Nothing runs the declared sweep, and nothing compares a declared pattern against what it matches. |
| The routing decision's pre-override input is overwritten by its output (**OBSERVED, not yet sited** — 280 left this unsited) | **CONFIRMED and SITED** | `_cmd_planning_lane.cmd_scope_estimate_heuristic` writes `references['scope_estimate']` — the pre-route guess. That field is the router's own S2 signal (`_read_scope_estimate`, consumed by `evaluate_signals_pure`). Its own docstring records the overwrite: *"The deep-lane refine Step 9 module-mapping derivation later overwrites the coarse guess when the deep lane runs"* (also at `classify_scope_pure` and the `SURGICAL` constant block). The `scope_provenance` explaining the guess is returned and logged but **never persisted**. The destruction is asymmetric: routing to **deep** destroys the input that selected deep; routing to **light** leaves it intact. So the evidence survives exactly when nobody needs it. |
| A staged premise EXPIRES; re-measure at outline (**OBSERVED**) | **CONFIRMED, and it converges with the row above** | B2's predicate reads `scope_estimate`. On the **light** lane refine Step 9 never runs, so B2 is reading phase-1-init's cheap pre-route guess — a premise staged four phases earlier — and using it to suppress validation. |
| Every remaining gap is still open (**HYPOTHESIS**) | **REFUTED in part — one item was closed, as the plan predicted** | See "Closed at HEAD" below. |

### Closed at HEAD — dropped, not re-scoped

**The `Files to survey:` / `Files expected to mutate:` fields were NOT merely unreconciled — they were
not parsed at all.** This is stronger than the plan's claim and subsumes it, so it is recorded as a
sharpening rather than a separate defect. `_plan_parsing._extract_affected_files` matched
`**Affected files:**` only; every extractor in `check-artifact-consistency.py` split on that one
heading. A survey-scope deliverable authored exactly as the standard mandates therefore:

1. parsed to an **empty** `affected_files` list;
2. **failed outline validation** with `Missing **Affected files:** section` (the validator and the
   authoring standard disagreed about what a declaration looks like);
3. had an **empty write-set**, so the bucket adjudication, the `module_testing` profile check and the
   phase-4-plan verification-only guard all saw a deliverable that touched nothing;
4. contributed nothing to `affected_files_recall`.

⇒ `outline-workflow-detail.md`'s statement that the recall check "runs against the
`**Files expected to mutate:**` subset" was **FALSE**. This is exactly the plan's
*"verification checks a spec's CITATIONS but not its ASSERTIONS"* sub-class: every citation in that
sentence resolved, and the behaviour claim did not hold.

## Deliverables

Commit `d9f9534` carries D1–D5. D0 mutated nothing and is recorded above.

### D1 — outline completeness is CLOSURE, not existence

**Done.** A new module, `manage-tasks/scripts/_qgate_closure.py`, computes the three closures the
plan names, and `_cmd_qgate_mechanical.cmd_qgate_mechanical` runs them as checks 7 and 8:

| Plan's closure | Function | What it computes |
|---|---|---|
| **projection** | `compute_projection_gaps` | Every declared write path is targeted by a step of a task belonging to that deliverable. |
| **referrer** | `compute_referrer_gaps` | Every non-verification step target is declared by its parent deliverable. `phase-4-plan/SKILL.md` § Step 5 already *stated* this ("Source each step's `intent` from the parent deliverable's `affected_files[N].intent`") and nothing checked it — *a stated invariant is not a checked invariant*, the generalisation the plan's Notes record. |
| **claim versus index** | `check_declared_scope_reconciliation` | Every declared glob expanded against the tree and reconciled with the enumerated declaration. |

*Done when* — **met, after round 1 found the first version of this fixture vacuous.**
`test_qgate_reports_closure_gap_while_files_exist_stays_clean` is the required fixture: real
repository files, `read`-intent steps, `files_exist` asserted at `0`, and the closure check still
reporting the incomplete set.

⛔ **The first version proved only half of that, and this report claimed the whole.** `files_exist`
applies an INTENT-DEPENDENT predicate — it requires existence for `read` and `delete`, inverts for
`write-new`, and skips `write-replace` outright — and every step in the fixture builder carried
`write-replace`. Its `files_exist: 0` was the skip, not a measurement: the round proved it by
replacing both paths with absent ones and watching all three end-to-end tests still pass. The steps
now carry `read` intent, and `test_files_exist_zero_is_load_bearing_not_vacuous` replaces the paths
with absent ones and asserts `files_exist` goes non-zero — so the zero asserted elsewhere is a
verdict the fixture could have failed.

### D2 — run the declared sweep before freezing the write-set

**Done, and it required an enabling fix D0 uncovered.** `check_declared_scope_reconciliation`
expands each declared glob (normalising it first, so a repo-escaping pattern is rejected as
unmeasured rather than walking out of the tree), enumerates the result **including hits outside the
declaration**, and emits one finding per declared glob — stating the total number of unenumerated
hits, naming a bounded prefix of them, and disclosing the remainder as `+N more` — naming the
resolution the author must pick
— widen with a recorded authorisation, or narrow and record the un-swept surface as a documented
exclusion. The `{declared scope wide, write-set narrow}` pair is therefore detected mechanically, by
comparing a declared glob against an enumerated file list, exactly as the plan specifies.

The enabling fix: the survey-scope declaration had to become machine-visible first (see D0 §
"Closed at HEAD"). `_plan_parsing` gains `extract_survey_scope` / `extract_mutation_scope`;
`extract_deliverables` carries both; `deliverable_write_set` unions the mutation scope;
`manage-solution-outline.validate_deliverable_contract` accepts the survey pair as satisfying the
section requirement; and `check-artifact-consistency.py` reads all three headings, which makes
`outline-workflow-detail.md`'s recall claim true rather than false.

⚠ **The survey pair is deliberately NOT folded into `affected_files`.** The outline validator's
check 3a rejects a wildcard in `affected_files` and 3b requires an intent marker on every entry —
both correct for the flat form, and both wrong for the survey pair, whose documented form carries no
markers and whose candidate pool may legitimately name a pattern. Folding them together would have
made every correctly-authored survey deliverable fail validation on two counts. The fields are
separate parsed members; the write-set unions them; the validator walks `affected_files` only.

The normative authoring rule — *run the sweep, enumerate including out-of-constraint hits, resolve
each explicitly* — is written into `outline-workflow-detail.md` § "The declared sweep is RUN before
the write-set is frozen", with the ⚠ that a prose warning is not a control and the mechanical check
is what makes it hold.

### D3 — assert `detector_population ⊇ fix_set_population` explicitly

**Done, as a normative line in two places rather than an implicit consequence of a root constant.**

- **Stated normatively** in `plan-marshall/workflow/q-gate-validation.md` § 2.9a, as a blockquote
  the Q-Gate checks are held to, alongside the mechanism that discharges it.
- **Discharged mechanically**: both closure checks return a `population` block;
  `cmd_qgate_mechanical` publishes it under `population` / `population_complete` and flips
  `ambiguous` when the population is incomplete — an unexpandable glob, an expansion stopped at the
  match ceiling, or a task naming a deliverable the outline lacks.

*Done when* — **met, after round 1 corrected both halves of this claim.**
`test_declared_glob_wider_than_the_enumeration_is_reported` asserts the slice is **non-empty** and
that **every known hit is named** in the finding. `test_declared_glob_fully_enumerated_is_closed`
asserts the complementary direction (no gap when the enumeration is complete) through counts; it
names no individual hit, and an earlier version of this row said both tests did.

⛔ **The expectation was also computed with the production expander's own call.** The expander *is*
`repo_root.glob(pattern)`, and the tests issued the identical call with the identical pattern — so
expectation and implementation agreed by construction and could not contradict each other. They now
derive the expected set by walking the tree and matching with `fnmatch`, a genuinely independent
oracle. Its walk prunes build and cache trees; that exclusion is stated at the helper, and every
pattern under test lives outside them.

The closure check's own population additionally publishes `scanned_paths` — the member IDENTITIES,
not only the cardinality. A count answers "was the population non-empty?"; only the members answer
"did it contain the element at risk?", which is the half of the plan's positive-population
requirement a count cannot express.

### D4 — a closure claim is a hint, never a licence

**Done, structurally rather than by exhortation.** The closure checks live in phase-4-plan **Step
8**, the unconditional inline script — not in Step 8b, the dispatched validator the surgical-scope
bypass suppresses. A closure claim therefore *cannot* reach them: there is no knob and no predicate
on the path that computes closure.

The normative line is added at the B2 predicate itself (`phase-4-plan/SKILL.md`), stating that B2
reaches the dispatched validators and nothing else, and naming why the bypass is self-reinforcing —
`affected_files_count` is the cardinality of the declaration under question, so under-enumeration
makes the suppression *more* likely.

*Done when* — **met, verified adversarially.**
`test_closure_check_runs_under_the_surgical_scope_bypass_shape` builds a plan satisfying B2 exactly
(`scope_estimate: surgical` persisted in `references.json`, two declared affected files), **asserts
that precondition positively** by counting the declared bullets in the fixture it just wrote, and
then asserts the closure check still runs and still fires.

### D5 — tests, each verified to fail pre-fix, plus the characterization-corpus rule

**Done.** 20 tests in `test_qgate_closure.py`, 3 in `test_recall_survey_scope.py`.

**Red-before-green was done by MUTATION, not by a stash.** A first attempt stashed the production
changes and ran the new suite: it produced a *collection error* (the new module was absent), which
proves the module did not exist and proves nothing about whether any guard detects its defect. That
is a weak red signal, so it was discarded in favour of a mutation campaign — each mutant reverting
one specific behaviour, each run against only the guard that names it.

**22 mutants, all detected**, re-derived by running the campaign at the moment of this claim. They
cover: the survey/mutation headings going unparsed; the write-set excluding the mutation scope; the
closure checks not being wired in; a home-relative glob reported as measured-empty; a referrer
closure accepting a target a declared glob would `fnmatch`; a projection closure reporting a declared
glob as unprojected; `population_complete` asserted rather than measured; the retrospective parser
reading one heading; `files_exist` skipped by `write-replace` intent; a repo-escaping glob; an
un-normalised in-repo `..` glob; a directory-only scope read as clean; an empty normalized
declaration entering the comparison; `population_complete` not reaching the caller as `ambiguous`;
a population publishing counts without identities; truncation applied silently; a hit list eliding
its remainder; the outline validator rejecting the survey pair; a lone survey field accepted as a
complete declaration; `extract_survey_scope` dropping its read default; and the survey pair being
invisible to both the foreign annotator and the phase-6 landing gate.

⛔ **The campaign found THREE vacuous guards across its two runs, which is why it was worth running
rather than reasoning about.**

1. **Round 1's own build.** `compute_referrer_gaps` filtered globs out of the comparison set, and
   that filter was a **no-op** — membership is literal string equality, so a pattern can only match a
   step target that is that same pattern string. The docstring explained a mechanism the code was not
   performing: an invented rationale in prose written to justify a guard. Both were corrected, and
   the guard now pins the property against the real alternative implementation (an `fnmatch`-accepting
   referrer closure) while asserting its own precondition — that the declared pattern genuinely
   matches the target.
2. **A redundant guard mistaken for a load-bearing one.** Mutating away the absolute-path check left
   the test green, because `Path.glob` raises on an absolute pattern and the exception handler
   produced the same verdict. Executing both cases settled it: `/etc/*.conf` raises
   `NotImplementedError`, while `~/x/*.py` **raises nothing and returns zero matches** — so the `~`
   half is the load-bearing one, and it now has the test. The code says which is which rather than
   presenting them as equivalent.
3. **A guard pointed at the wrong suite.** The phase-6 landing-gate fix was mutated against a suite
   that does not exercise that gate, which passed. The gate had no coverage at all; it now has a
   guard in its own suite, built so a regression reaches the opposite verdict — no foreign paths
   found — rather than a shorter list.

**The characterization-corpus rule, discharged by enumeration rather than by selection.** The corpus
is the fixture set of `test_manage_tasks_qgate_mechanical.py`, enumerated mechanically — every
fixture in the file, via `grep -n "affected_files\|'target':"` — not chosen. The sweep found the
corpus **systematically endorsed the defect**: every fixture declared one path (`src/A.java`) while
its tasks targeted another (a real marketplace file), so every fixture carried an unclosed declared
set, and `test_qgate_mechanical_clean_plan_passes_all_checks` asserted `total_failed == 0` over it.
An under-enumerated corpus faithfully pins the defect as expected behaviour; this one did.

The corpus was **aligned, not exempted**: `_EXISTING_FILE` is now both the declared path and the step
target in every fixture that is not deliberately injecting a fault.

**Stated exclusions** — every fixture that does NOT declare the path its task targets, with its
reason:

| Fixture | Why it deviates | Disposition |
|---|---|---|
| `test_qgate_mechanical_coverage_missing_deliverable` and the two persist fixtures (`_seed_one_coverage_failure`, `test_qgate_mechanical_emit_writes_findings`) | Deliverable 2 deliberately has NO task — that is the coverage fault under test. A write-intent declaration there would fire the projection closure as a genuine SECOND fault, so these tests would no longer measure one check. | Declared `(read)`. A deliverable with no tasks and only read-intent declarations owes no projection, so the injected fault stays singular. Recorded rather than left implicit — this is a fixture shaped to isolate a check, not a claim that read-only task-less deliverables are ordinary. |
| `test_qgate_mechanical_files_exist_missing_step_target` | Both paths must be ABSENT from disk — that is the files_exist fault under test. | Declares `_MISSING_FILE`, the same path its step targets, so its only fault is the intended one. |
| The verification-profile fixtures (`'target': 'pw verify'`, `'pw verify --module plan-marshall'`) | Their steps are COMMANDS, not paths. | Excluded from the closure pass by profile, in production code — `check_declared_set_closure` skips verification tasks, matching `_check_files_exist`. Pinned by `test_verification_tasks_are_excluded_from_the_scanned_population`. |

The `_ALL_CHECKS` tuple in that file is additionally cross-checked against the LIVE result's own key
set (`assert set(result['checks']) == set(_ALL_CHECKS)`), so a check added to the script without an
entry here fails loudly instead of going silently unasserted. A hard-coded name list stops covering
whatever is added after it; quantifying over the produced set does not.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** — six production scripts and
five test modules — so the full gate applies. The working tree was clean at Step 2, and re-asserted
clean before this diff was taken, so nothing staged or untracked is invisible to it.

- **Per-commit gate**: `./pw quality-gate` before each `*.py`-touching commit, read from the tools'
  own streamed output (the direct-`./pw` path emits no TOON log): `Success: no issues found in 414
  source files`, `All checks passed!`, `>>> quality-gate: SPDX-header check passed`. Its first run
  reported one real `mypy` error (`_qgate_closure.py`, `int(Any | None)`), fixed by a typed `_as_int`
  helper before the commit.
- **Branch gate**: `./pw verify`. ⚠ **It ran three times and the SECOND run FAILED** — recorded
  because the failure is the exact one this gate exists for.

  | Run | Result |
  |---|---|
  | 1 (initial implementation) | `=== verify: SUCCESS ===`, `20814 passed, 14 skipped in 558.48s` |
  | 2 (after the round-1 fixes) | **`verify: test-compile failed`** — `mypy` over the test tree rejected `test_survey_scope_declaration.py::_only_deliverable`, `Returning Any from function declared to return "dict[Any, Any]"` |
  | 3 (after the annotation fix) | see § "Final gate" below |

  ⛔ **`test-compile` is the sub-step neither narrower call runs.** `./pw verify` is exactly
  quality-gate + test-compile + module-tests (`build.py::cmd_verify`), and only `test-compile`
  type-checks the tests. Round 1's fixes were iterated with `uv run pytest` on single files and
  checked with `./pw quality-gate` — both green throughout — while a test-only type error sat in the
  tree the whole time. It would have surfaced on CI and nowhere earlier. This is the lane contract's
  warning reproduced verbatim: the narrower calls do not add up to the gate.

  Read from the streamed output, not the exit code — **the wrapper exited 0 on the failing run**, so
  `SUCCESS` versus `test-compile failed` is the only signal.

- Every `./pw` call carried `UV_HTTP_TIMEOUT=600`; the branch gate exceeds the 600 s foreground Bash
  timeout and was run in the background each time.

**Final gate** — _filled in below once the last verify run lands; it is deliberately not written
ahead of the result._
