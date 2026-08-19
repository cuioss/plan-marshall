# Gaps — 280-outline-plan-scope-derivation-integrity

Arm B of this plan shipped working, correct, mutation-verified code: the published `worktree_state`
discriminator has one owner and six consumers that branch on it, and outline classification is
derived from the write-set. What remains is not in that machinery. Two stub sites in the very corpus
D5's population rule governs were swept up and then left behind unconverted and undeclared, which
makes the report's coverage sentence false and the population rule undischarged. **Six** documentation
surfaces still describe the pre-materialization framing the fix removed — two of them (G4, G5) about
the `get-module-context` degrade, and four more (G13) explaining an unresolvable footprint by
pre-materialization alone, one of those inside a file this plan edited two lines of, nine hundred lines
from the line the plan corrected. One regression test has since stopped discriminating the defect it
names (proved by mutation — and no other test in its bundle catches it either). One deliverable clause
(D4's footprint precondition) was disclosed as deferred and remains open in the successor plan too. The
rest are report-level count and traceability defects.

## G1 — Convert the retired-boolean seam stub in `test_freshness_notation_crosscheck.py`'s autouse fixture

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py:166`
  (fixture `_stub_resolver_seam`)
- **Evidence:** the stub reads
  `monkeypatch.setattr(file_ops, '_query_worktree_path', lambda _plan_id: (True, str(Path.cwd())))`.
  The seam yields `(worktree_state, worktree_path)` since #1283, so `True` is not a member of
  `file_ops.VALID_WORKTREE_STATES`. Demonstrated directly: with such a stub installed,
  `PlanContext.worktree_state` returns `True`, `has_worktree` returns `False`, and `worktree_path`
  resolves to `cwd_checkout_root()` rather than to the stubbed path. The fixture is `autouse`, so all
  17 tests in the module run through it. `git show aeab5ab:test/.../test_freshness_notation_crosscheck.py`
  confirms both sites were present, unconverted, at the merge commit — the file landed on `main` in
  `e2b6665` (#1279) about 35 minutes before #1283 merged.
- **Why it matters:** this is the F16/F20 defect class, two instances past the run that claimed to
  have closed it. Today the tests pass either way (replacing the stub with
  `('materialized', '/nonexistent/xyz')` still gives 17 passed, because `compute_worktree_sha` is
  separately stubbed), so the harm is latent: the moment `_cmd_pre_commit_verify_freshness` or
  anything below it branches on `worktree_state`, these 17 tests silently exercise the
  `disabled`/fallback path while looking like they exercise a materialized worktree.
- **Action:** replace the lambda with
  `lambda _plan_id: worktree_query_result(True, str(Path.cwd()))`, importing
  `worktree_query_result` from `_resolve_project_dir_fixtures` exactly as the sibling module
  `test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness.py:59,268-269` already does.
- **Done when:** `grep -rn "_query_worktree_path" test/ --include=*.py -A2 | grep -E "\((True|False),"`
  returns no hand-written tuple outside `_resolve_project_dir_fixtures.py`, and
  `test_freshness_notation_crosscheck.py` still passes (17 tests).
- **Effort:** S
- **Risk if fixed:** none expected — the derived value for `(True, <non-empty path>)` is
  `('materialized', <path>)`, which routes the consumer to the same directory the fallback currently
  yields under the harness. If any assertion depends on the fallback, it will surface as a failure in
  that module alone.

## G2 — Convert the retired-boolean seam stub in the live-resolution test

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py:563`
  (inside `test_the_real_resolution_path_refuses_and_corroborates_against_this_repository`)
- **Evidence:** `monkeypatch.setattr(file_ops, '_query_worktree_path', lambda _plan_id: (True, str(PROJECT_ROOT)))`
  — the same retired shape as G1, at a second site, overriding the autouse fixture for this one case.
  Same population, same absent exclusion row.
- **Why it matters:** this is the module's one deliberately non-hermetic case — it drives the gate
  with no resolver stub so a resolver that stopped working is a failure rather than a silent
  `unverified` pass. That intent depends on the test standing in the real repository root; a stub
  whose first element the consumer discards means the root it lands on is a coincidence of the
  harness's cwd, not the value the test names.
- **Action:** same as G1 — `worktree_query_result(True, str(PROJECT_ROOT))`.
- **Done when:** the same grep is clean and the case still passes.
- **Effort:** S
- **Risk if fixed:** none expected; same reasoning as G1.

## G3 — Correct the run report's characterization-corpus coverage claim

- **Kind:** report-defect
- **Severity:** medium
- **Topic:** tests
- **Where:** `doc/plans/code-intelligence-substrate/280-outline-plan-scope-derivation-integrity/report-01.md`
  § The characterization corpus (D5's population rule), the sentence beginning
  "**Every stub SITE is covered, and the coverage is structural rather than per-file.**"
- **Evidence:** two sites in the swept population — `test_freshness_notation_crosscheck.py:166` and
  `:563` (G1, G2) — are neither converted nor listed in the four-row exclusion table. The population
  *enumeration* in that section is accurate (I re-derived the identical 13-bundle set), so the defect
  is in the conclusion drawn from it, not in the sweep. The section already carries the corrected
  form of this exact mistake — "⛔ **'Site', not 'module', and the distinction cost two defects**" —
  and the correction still missed two more sites in the same bundle it was written about.
- **Why it matters:** D5's contract states that *"an unstated exclusion is indistinguishable from an
  endorsement of the behaviour on the excluded case."* A coverage sentence asserting completeness is
  worse than no sentence: it is the exact "invented rationale" failure mode the run's own § What have
  we learned proposes a contract rule against, committed a third time in the same document.
- **Action:** amend the section to name both sites, state whether each is converted (after G1/G2) or
  excluded with a reason, and replace the absolute coverage claim with one bounded by what was
  actually verified — e.g. the grep command re-run and its output pasted.
- **Done when:** the report's corpus section accounts for every file returned by
  `grep -rln "_query_worktree_path\|_parse_get_worktree_path_output" test/ --include=*.py`
  (25 files at this HEAD), each either converted or excluded with a stated reason.
- **Effort:** S
- **Risk if fixed:** none — documentation only.

## G4 — Correct the stale degrade rationale in `_stamp_read_provenance`'s docstring

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py:946-950`
  (docstring of `_stamp_read_provenance`)
- **Evidence:** the docstring reads: *"`get-module-context` degrades to the cwd-relative checkout
  root when the plan declares `use_worktree=true` but its worktree is not materialized yet (see the
  `WorktreeResolutionError` branch in `main`)."* The branch it points at, at `:1108-1123` of the same
  file, states the opposite: *"This degrade no longer covers the pre-materialization window, and must
  not be read as though it does … the shared resolver now branches on the producer's `worktree_state`
  discriminator and returns the main checkout for it — so this verb never sees an exception for the
  ordinary phase-3-outline window."* The shipped test agrees with the branch, not the docstring:
  `test/plan-marshall/manage-solution-outline/test_get_module_context.py:517` asserts
  `data['worktree_fallback'] is False` for `worktree_state: pending`.
- **Why it matters:** a reader deciding what `worktree_fallback` means will conclude that a normal
  phase-3 read stamps `worktree_fallback: true`. It stamps `false`. Two contradictory statements about
  the same field sit in one file, and the wrong one is the one attached to the function that produces
  the field. This is precisely the "stale rationale" class the run's own F6–F11 sweep existed to
  clear, missed inside a file the run edited.
- **Action:** rewrite the docstring's first paragraph to name the genuine-failure cases the degrade
  now covers — executor not locatable, `manage-status` failure, payload with no recognised state —
  and state that the pre-materialization window resolves through the discriminator without degrading.
- **Done when:** the docstring and the `main()` comment at `:1108-1123` make the same claim, and
  neither names the pre-materialization window as a degrade cause.
- **Effort:** S
- **Risk if fixed:** none — comment only.

## G5 — Correct the stale degrade rationale in `manage-solution-outline/SKILL.md`

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md:245`
- **Evidence:** *"The fallback exists because a plan declaring `use_worktree=true` has no materialized
  worktree until phase-5-execute, while `phase-3-outline` — the phase that consumes this verb — runs
  before that."* That is the `pending` state, which since #1283 resolves to the main checkout through
  the discriminator with **no** fallback stamped. The table two lines above (`:242`) compounds it:
  `worktree_fallback` is described as `true` "when `--plan-id` named a plan whose worktree could not
  be resolved", which is now only the genuine-failure set.
- **Why it matters:** this is the skill's normative contract for the `worktree_fallback` field. An
  agent reading it will expect the fallback to fire in the ordinary phase-3 window and will
  mis-interpret `worktree_fallback: false` as evidence that a worktree was used. The run's own F26/F27
  sweep fixed the equivalent sentences in `tools-file-ops/SKILL.md` and
  `workflow-integration-git/standards/worktree-handling.md`; this third SKILL.md was not reached.
- **Action:** replace the rationale sentence with one naming the genuine-failure causes, and note that
  a `pending` plan resolves to the checkout root through the published state without stamping a
  fallback. Keep the field table, adjusting the `worktree_fallback` row to match.
- **Done when:** no sentence in this SKILL.md attributes the fallback to the pre-materialization
  window, and the field table's `worktree_fallback` row names resolution *failure* rather than
  "could not be resolved".
- **Effort:** S
- **Risk if fixed:** none — documentation only. Coordinate with G4 so both surfaces say the same thing.

## G6 — Restore discrimination to the unparseable-outline regression test

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/manage-tasks/test_qgate_keyword_drift_reads_prose.py:147`
  (`test_heading_less_deliverables_section_is_unparseable`), guarding
  `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_qgate_mechanical.py:159-166`
- **Evidence:** mutation-proved. Changing the empty-deliverables branch of `_load_deliverables` from
  `return [], {}, False` to `return [], {}, True` — i.e. restoring the exact F35 defect — leaves the
  file **green: 5 passed**. The reason is `_cmd_qgate_mechanical.py:728`,
  `ambiguous = not parseable or not population_complete`: the fixture's task references deliverable 1,
  which the heading-less outline does not define, so the closure population is incomplete and
  `ambiguous` is True whatever `parseable` says. At the merge commit the assertion was carried by
  `parseable` alone (`git show aeab5ab:.../\_cmd_qgate_mechanical.py` line 653 reads
  `ambiguous = not parseable`); plan 350 (#1295) widened the expression and the test silently stopped
  discriminating.
- **Why it matters:** F35 was a real defect — a detector reporting zero findings over an empty set
  while telling the orchestrator the mechanical pass was authoritative. Its only regression guard no
  longer fails if the defect returns. The test's own docstring still claims to pin that behaviour, so
  the guard reads as present while being inert.
- **Action:** assert the discriminating value directly rather than the combined flag — e.g. call
  `_load_deliverables` and assert it returns `parseable is False`, or add a second case whose task
  references no missing deliverable so `population_complete` stays True and `ambiguous` is carried by
  `parseable` alone.
- **Done when:** re-running the mutation above (empty-deliverables branch returns `True`) makes the
  file go red.
- **Effort:** S
- **Risk if fixed:** none — test-only.

## G7 — Re-derive the diff-scope counts in the run report's § Build gate

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `report-01.md` § Build gate, first bullet: "the diff changes production Python in six
  bundles plus eight test modules"
- **Evidence:** re-derived from the merge commit. Production `*.py` changes land in **nine** skills,
  all inside the single `plan-marshall` bundle — `manage-execution-manifest`, `manage-references`,
  `manage-solution-outline`, `manage-status`, `manage-tasks`, `plan-marshall`, `script-shared`,
  `tools-file-ops`, `workflow-integration-git`. Test modules changed:
  `git show aeab5ab --name-only --format="" | grep "\.py$" | grep "^test" | wc -l` → **23**, not eight.
- **Why it matters:** the plan's own claim-label table ends with *"Any count quoted in this plan —
  LEAD, not a fact. Never carry a count forward … Re-derive from the live tree at the moment of
  consumption."* The build-gate figures were re-derived (the test-collection count carries an explicit
  re-derivation note); these two were not, and they were the ones describing the diff the gate ran over.
- **Action:** replace both numbers with re-derived values and state the command each came from, or
  drop the counts and describe the scope qualitatively.
- **Done when:** every count in § Build gate is either accompanied by the command that produced it or
  removed.
- **Effort:** S
- **Risk if fixed:** none — documentation only.

## G8 — Correct the commit count in the run report's contract-check table

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `report-01.md` § Contract check (Step 9), row "4 Implement": "Six commits, every one
  carrying the `Co-Authored-By: Claude` trailer"
- **Evidence:** the GitHub API reports `commits: 11` for PR #1283, and all eleven are listed with the
  trailer present. Six was correct when the row was written (commit `8e175f7` was the seventh, the
  first being the Step-3 `git mv` accounted for in its own row); four further commits — `15f1988`,
  `5d3673f`, `b34ec31`, `817d959` — landed afterwards and the row was never re-derived.
- **Why it matters:** the row's own framing is *"verified by reading the trailers back out of the
  log"*, which is a claim about a set whose size the row states wrongly. The trailer half of the claim
  is true of all eleven, so the defect is confined to the count.
- **Action:** state the count as re-derived at the final commit, or express it as "every commit on the
  branch" and drop the number.
- **Done when:** the row's count matches the PR's commit count, or carries no number.
- **Effort:** S
- **Risk if fixed:** none — documentation only.

## G9 — Record the disposition of D2 and D3 in the run report

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `report-01.md` § Deliverables — it carries `### D1`, `### D4`, `### D5` and `### D0`
  headings and nothing for D2 or D3
- **Evidence:** `grep -n "D2\|D3\b" report-01.md` returns nothing. The plan's D2 (closure, not
  existence) and D3 (a closure claim is a hint, never a licence) are never mentioned. They did go to
  arm A — `350-outline-derived-set-closure-integrity/plan.md:101-120` carries them as its D1–D4, and
  350's report records D4 as delivered — but that is discoverable only from the successor spec.
- **Why it matters:** the plan says *"⚠ If a deliverable grows a further arm, split it out rather than
  absorbing it silently."* Splitting them out was correct; not saying so is the silent half. A reader
  auditing this plan against its contract cannot distinguish "deferred to arm A" from "forgotten",
  which is the same traceability failure the plan's D0 exists to prevent for defects.
- **Action:** add two rows (or a short paragraph) to § Deliverables stating that D2 and D3 are arm-A
  material, naming the successor plan and the deliverable numbers they became.
- **Done when:** every deliverable D0–D5 in `plan.md` has an explicit disposition somewhere in
  `report-01.md`.
- **Effort:** S
- **Risk if fixed:** none — documentation only.

## G10 — Report a missing `<!-- bucket: -->` comment, not only a wrong one

- **Kind:** omission
- **Severity:** low
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py:243-245`
  (`_check_declared_bucket`), against
  `marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/outline-workflow-detail.md:315`
- **Evidence:** the standard states: *"the resolved bucket MUST be recorded as a comment on the
  `**Profiles:**` line … The comment is normative … **A missing or wrong bucket comment is a Q-Gate
  finding.**"* `phase-3-outline/SKILL.md:467` repeats that the comment is REQUIRED. The check
  implements only the *wrong* half, in one direction: `if not declared or not write_set: return []`.
  No other consumer of `declared_bucket` exists (`grep -rn "declared_bucket" marketplace/` returns
  only `_plan_parsing.py` and this function), so a deliverable with no bucket comment passes
  validation silently.
- **Why it matters:** this plan is the one that made the bucket comment machine-readable for the first
  time. It is exactly the "a stated invariant is not a checked invariant" generalisation the plan's own
  Notes record. A missing bucket also disables the wrong-bucket check entirely, so the un-recorded case
  is strictly weaker than the mis-recorded one — the cheapest way to evade the new check is to delete
  the comment.
- **Action:** emit a validation warning (not an error — an error would break existing outlines) when a
  deliverable carries no `declared_bucket`, and a warning when the declared value is outside the
  documented six-bucket vocabulary (`production_only|test_only|documentation_only|mixed_code|mixed_with_docs|unknown`).
- **Done when:** `validate_deliverable_contract` on a deliverable with a non-empty write-set and no
  bucket comment yields a warning naming the missing audit trail, with a paired negative asserting a
  present bucket yields none.
- **Effort:** S
- **Risk if fixed:** existing outlines authored before the comment was enforced would start emitting
  warnings; keeping it a warning rather than an error contains that. Check the phase-3 gate's
  warning-handling before choosing severity.

## G11 — Make the bucket check's import fail-open observable

- **Kind:** bug
- **Severity:** low
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py:184-203`
  (`_write_set_is_all_documentation`), consumed at `:248-249`
- **Evidence:** the function returns `None` on `ImportError` and the caller writes
  `if not _write_set_is_all_documentation(write_set): return []`. `None` is falsy, so an unavailable
  `_manifest_core` makes the whole bucket check vanish with no signal of any kind — no warning, no
  info field, nothing distinguishing "checked and clean" from "could not check". The fail-open is
  documented and deliberate, and it is currently unreachable in practice: the executor puts every
  skill's `scripts/` directory on `PYTHONPATH` (`generate_executor.py:1247`, via `collect_script_dirs`),
  and the test suite reaches the real predicate (mutating the comparison at `:246` turns
  `test_bucket_comparison_is_case_insensitive` red, which requires the import to have succeeded).
- **Why it matters:** this is the shape the plan's own thesis warns about — a guard that cannot be
  distinguished from a guard that passed. If the import ever breaks (a bundle rename, a packaging
  change, an extension-loading regression), phase-3 outlines silently lose the bucket adjudication and
  every downstream profile assignment rides on an unchecked claim.
- **Action:** on `ImportError`, append a warning (not an error) naming the unavailable predicate, so
  the skipped check appears in the validator's output instead of resolving to silence. The call site
  already separates `errors` from `warnings`, so this needs no signature change beyond returning the
  tri-state to a caller that can surface it.
- **Done when:** a test that patches the import to fail asserts a warning is produced and no bucket
  error is raised.
- **Effort:** S
- **Risk if fixed:** a warning would surface in any environment where the import genuinely fails,
  which is the intent; confirm no test harness deliberately runs without `manage-execution-manifest`
  on the path before landing.

## G12 — Close or re-scope D4's undelivered footprint-precondition clause

- **Kind:** incomplete
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/extension_base.py:565-596`
  (`_resolve_plan_footprint`), plus the peer gates named in the same docstring
  (`manage-references.resolve_live_worktree`, the composer's `_resolve_footprint`)
- **Evidence:** D4's *Done when* requires "a footprint-derived precondition is evaluated at planning
  time rather than at finalize". `_resolve_plan_footprint` still returns `None` — permanently
  unresolvable — for a `disabled` plan whose footprint *is* derivable from the main checkout. The
  report discloses this (§ D4, F13) and hands it to arm A; arm A recorded it **not scoped**
  (`doc/plans/code-intelligence-substrate/350-outline-derived-set-closure-integrity/actual-state.md:130`),
  so no plan currently owns it.
- **Why it matters:** every footprint gate in the tree reports "no evidence" for a whole class of
  plans whose evidence exists, which is a measurement that misreports by construction. It is a small
  gap only because the two reasons the run gave for reverting are real and load-bearing: resolving a
  `disabled` plan's footprint makes `not_necessary` reachable at early compose, and
  `manage-execution-manifest.py:736-789` drops `pre-push-quality-gate` on exactly that verdict — the
  first failure this plan's own Problem statement names.
- **Action:** decide the policy once, across all three gates together: either derive a `disabled`
  plan's footprint from the main checkout **and** make the early-compose window explicitly ineligible
  for the `not_necessary` prefilter, or state in the shared docstring that the policy is permanent and
  remove the "derivable but not derived" framing so it stops reading as debt.
- **Done when:** `extension_base._resolve_plan_footprint`, `manage-references.resolve_live_worktree`
  and the composer's `_resolve_footprint` agree on a single documented policy for `disabled`, and a
  test pins that `pre-push-quality-gate` survives an empty early-compose diff under whichever policy
  is chosen.
- **Effort:** M
- **Risk if fixed:** high blast radius — this is why the run reverted it. A dropped
  `pre-push-quality-gate`, or footprint derivation that reads unrelated uncommitted state in the main
  checkout, are both regressions the current behaviour prevents. Any change needs the three gates
  moved together and the early-compose case pinned first.
