# Gaps — 350-outline-derived-set-closure-integrity

The shipped closure machinery is sound: D1–D4 are implemented as specified, every load-bearing guard
was proven non-vacuous by mutation (eight mutants, eight detected), and no fail-open was found on the
closure path. What remains splits three ways. **(a) Record integrity** — run 02's rebase silently
dropped two of run 01's commits, so the landed `report-01.md` carries a count run 01 had already
corrected and loses a build-gate result run 01 had already recorded, while `report-02.md` states that
every commit's tree was preserved (G1–G6, G19). **(b) One real coverage hole in the shipped code** — a
declared glob in a deliverable's write-set is enforced by neither closure when it matches nothing yet
(G8), plus a false clause in operator-facing spec text (G9) and a byte-exact dedupe contradicting its
own docstring (G16). **(c) Declared residue, all confirmed still open** (G7, G10–G15). D5 is the one
partial deliverable: the tests are real, but the characterization-corpus **rule** was applied without
being codified anywhere a later run would find it (G17).

## G1 — Correct `report-02.md`'s account of the rebase: two of run 01's eleven commits were dropped

- **Kind:** report-defect
- **Severity:** medium
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/350-outline-derived-set-closure-integrity/report-02.md:19-36` (§ "How run 01's work was recovered")
- **Evidence:** The section states run 01 "committed and pushed **nine** commits", that "run 01's nine
  commits were **rebased** onto current `origin/main`", and that "the rebase was conflict-free, and
  **every commit's tree is preserved**". Re-derived:
  `git log --oneline eb0124c..origin/claude/derived-set-closure-integrity-g7n8x2 | wc -l` → **11**.
  Only the first nine (through `ce4292c`) reached the branch that became PR #1295; `f614b9a`
  ("docs(plans): record the final clean verify result") and `33392fd` ("docs(plans): correct the
  report header and the stale commit enumeration") did not. Proof that the merged text is
  `ce4292c`'s: `git show ce4292c:…/report-01.md` diffed against the landed `report-01.md` differs
  only in the rewritten commit SHAs and in run 02's own round-4 edits (A1, A2, A3, A7, A8 and the
  header block) — the two dropped commits' hunks are absent from both.
  ⚠ **The mechanism is not determinable from the tree, and the entry does not assert one.** The two
  commits are dated `10:59:37` and `11:00:00` UTC and run 02's first commit `d898934` is dated
  `11:03:13` — so a fetch taken before run 01's last push explains the loss as well as a rebase that
  dropped them. What is established is the *effect*: two of run 01's eleven commits are absent from
  the landed tree while `report-02.md` asserts nine were pushed and every tree preserved.
  ⛔ **Bound:** both dropped commits touch only `report-01.md` and `actual-state.md`
  (`git show --stat`), so **no production code and no test was lost** — the loss is confined to the
  record, which is why this and G2–G4 are report-defects rather than code gaps.
- **Why it matters:** The claim reads as an assurance that nothing was lost, and it is what a later
  reader would rely on rather than re-deriving. Two documented corrections — one of them a correction
  the same run's own contract-change proposal is about — were destroyed by the recovery step and the
  destruction is asserted not to have happened.
- **Action:** Replace the paragraph with the re-derived figures: run 01's branch carries 11 commits
  above `eb0124c`; 9 reached the branch under review; `f614b9a` and `33392fd` did not, and their
  content is restored by G2 and G3. Name `origin/claude/derived-set-closure-integrity-g7n8x2` as the
  surviving source, and state that the mechanism (a rebase that dropped them, or a fetch that
  predated their push) is not recoverable.
- **Done when:** `report-02.md` § "How run 01's work was recovered" states 11 and 9, names the two
  commits that did not carry over, and no longer claims every tree was preserved.
- **Effort:** S
- **Risk if fixed:** None — a documentation record.

## G2 — Restore run 01's corrected deliverable-commit enumeration in `report-01.md`

- **Kind:** report-defect
- **Severity:** medium
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/350-outline-derived-set-closure-integrity/report-01.md:73`
- **Evidence:** The line reads "D1–D5 land across **four** commits: `3b57b7e` …, `9d257dd` and
  `4ec39fd` …, and the round-2 fix commit …". The round-3 fix commit (`0f10d16` pre-rebase, "fix(qgate):
  repair a population regression round 2 introduced") is absent. Run 01 fixed exactly this in
  `33392fd`, whose message reads: "The deliverable-commit line said 'four commits' and omitted the
  round-3 fix. That sentence has now been wrong twice … so it names the commits instead of counting
  them." That fix is not in the landed tree.
- **Why it matters:** The paragraph's own ⚠ warns the reader that this line has been wrong before, and
  then presents a wrong version. A reader reconstructing which commit carried which fix is misled about
  the round-3 population regression — the most consequential defect the run found in its own work.
- **Action:** Replace the sentence with `33392fd`'s named list (recoverable verbatim from
  `git show 33392fd -- …/report-01.md`), rewriting the pre-rebase SHAs to a form that resolves — since
  the PR was squash-merged as `63943f5` and branch `…-3i53aj` is gone, name the commits by their
  `g7n8x2` SHAs and say which branch they live on.
- **Done when:** `report-01.md` § Deliverables names five deliverable-bearing commits, including the
  round-3 fix, and every SHA it quotes resolves on a ref this repository still has.
- **Effort:** S
- **Risk if fixed:** None.

## G3 — Restore the recorded final build gate in `report-01.md`

- **Kind:** report-defect
- **Severity:** medium
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/350-outline-derived-set-closure-integrity/report-01.md:331-338`
- **Evidence:** The section reads "**Final gate** — _pending a clean re-run._ … The gate is re-run once
  no other process is touching the tree, and the result recorded **here** with its pytest summary
  re-derived at the moment of the claim." It was re-run and it was recorded: `f614b9a` replaced this
  paragraph with `=== verify: SUCCESS ===` / `20840 passed, 14 skipped in 385.92s (0:06:25)` at
  `0f10d16`, run with nothing else touching the tree, plus the six-sub-dimension coverage line. The
  rebase dropped it, so the document now carries an unfulfilled promise and no gate.
- **Why it matters:** Run 01's build-gate record is the only evidence that the halted run's committed
  state was verified undisturbed. `report-02.md`'s gate measures a different head (`117d351`) after
  further commits, so it does not substitute.
- **Action:** Restore `f614b9a`'s § Final gate text verbatim (`git show f614b9a -- …/report-01.md`),
  adjusting only the commit reference to one that resolves.
- **Done when:** `report-01.md` § Final gate states a measured result rather than a pending promise.
- **Effort:** S
- **Risk if fixed:** None.

## G4 — Correct `actual-state.md` § 7: run 01 did record a final gate

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/350-outline-derived-set-closure-integrity/actual-state.md:168-170`
- **Evidence:** "Run 01 recorded **no** final gate — its § Final gate says 'pending a clean re-run' —
  so the final gate is the one run 02 ran". This sentence was written by run 02 as fix A5, on top of a
  document state its own rebase had reverted. `f614b9a` shows run 01 recorded one.
- **Why it matters:** It converts an artefact of the recovery step into a statement about run 01's
  conduct, and it is the sentence that sends a reader away from the record instead of to it.
- **Action:** After G3 restores the record, change the pointer to name run 01's own final gate and
  keep the reference to run 02's gate as the separate, later measurement it is.
- **Done when:** `actual-state.md` § 7 no longer asserts that run 01 recorded no final gate.
- **Effort:** S
- **Risk if fixed:** None.

## G5 — Re-derive `report-01.md` § D5's new-test counts; three of five figures and the total are wrong

- **Kind:** report-defect
- **Severity:** low
- **Topic:** tests
- **Where:** `doc/plans/code-intelligence-substrate/350-outline-derived-set-closure-integrity/report-01.md:184-192`
- **Evidence:** The paragraph claims, "Re-derived with `grep -c '^def test_'` at the moment of this
  claim … **34** in `test_qgate_closure.py`, **8** in `test_survey_scope_declaration.py`, **4** in
  `test_recall_survey_scope.py`, **1** added to `test_foreign_deliverable_column.py` (11 → 12) and **2**
  to `test_foreign_pr_gate.py` (13 → 15) — **49** new test functions". Re-derived at HEAD with the same
  command: **36**, **10**, **5**, 12 (pre-merge 11), 15 (pre-merge 13) — **54**. No commit after the
  merge touched those files (`git log --oneline 63943f5..HEAD -- <the three new files>` is empty), so
  the drift arose inside the run.
- **Why it matters:** This is the third recorded false version of this one sentence (report-02 § A1
  fixed the previous one and asserted the figures were re-derived). A count presented as freshly
  measured, and wrong, is worse than no count.
- **Action:** Follow `33392fd`'s own rule and stop counting: name the five modules and state each
  count alongside the command and the ref it was measured at, or drop the total.
- **Done when:** every figure in § D5 reproduces from `grep -c '^def test_'` against the named ref.
- **Effort:** S
- **Risk if fixed:** None.

## G6 — Correct `report-02.md`'s "six sites" for the raw task-number conversion

- **Kind:** report-defect
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `doc/plans/code-intelligence-substrate/350-outline-derived-set-closure-integrity/report-02.md:242-246` (§ F-R1, "Sweep-and-count on the same claim")
- **Evidence:** "The identical raw pattern appears at **six** sites in `_cmd_qgate_mechanical.py`."
  Re-derived: `int(x['number'])` appears at `_cmd_qgate_mechanical.py:154, 184, 296, 300, 309, 310,
  311, 502` — **eight** — and two further sites feed a bare `t['number']` to a `:03d` format
  (`:243`, `:371`), which raises on the same inputs. No grouping of the file's occurrences yields six.
- **Why it matters:** The paragraph is the sweep-and-count discipline applied to the reviewer's finding;
  a wrong denominator understates the residue G7 has to clear, and the whole point of the sweep is that
  the count is the deliverable.
- **Action:** Re-run the sweep, state the pattern used, and record 8 (conversions) + 2 (unguarded
  format sites) with their line numbers.
- **Done when:** the figure in § F-R1 matches a grep a reader can re-run.
- **Effort:** S
- **Risk if fixed:** None.

## G7 — Guard the remaining unchecked task/deliverable `number` conversions in `_cmd_qgate_mechanical.py`

- **Kind:** bug
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_qgate_mechanical.py:154`, `:184`, `:243`, `:296`, `:300`, `:309`, `:310`, `:311`, `:371`, `:502`
- **Evidence:** All ten read a `number` field straight off a JSON record.
  `:243` (`number = t['number']`, then `f'files_exist: TASK-{number:03d}…'` at `:393`) and `:371` raise
  `TypeError` on a `None` or string value before the finding is built; the eight `int(…)` sites raise
  `KeyError` / `TypeError` / `ValueError`. `_qgate_closure.py:85` already ships the fix (`_as_int`) and
  `_qgate_closure.py:376-383` documents exactly why it matters: these accesses sit on the path that
  **emits** a finding, so the gate crashes when it has something to report and passes when it does not.
  Declared as residue in `report-02.md:572` and confirmed open here.
- **Why it matters:** A fail-open inside the mechanical Q-Gate — the same class `cuioss-review-bot`
  found in the new module (F-R1), at sites the module's own sibling still carries. `_check_files_exist`
  and `_check_acyclic` are the two checks with the widest reach.
- **Action:** Import `_as_int` from `_qgate_closure` (or lift it into a shared helper) and apply it at
  all ten sites, rendering an unusable number as `000` exactly as the closure does. Where a deliverable
  number is unusable, drop the record from the map and let the population report the loss rather than
  raising.
- **Done when:** a parametrized regression test seeds a task whose `number` is `None`, `''` and
  `'holistic'`, plus one with the key absent, and `cmd_qgate_mechanical` returns a normal result with
  the expected findings for each; mutating any guard back to a raw conversion turns it red.
- **Effort:** M
- **Risk if fixed:** Low — a task whose number is currently a float or numeric string would render
  identically; the only behaviour change is on records that today crash.

## G8 — Close the glob-shaped write-set that neither closure can examine

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_qgate_closure.py:177` (`compute_projection_gaps`, the `not is_glob(p)` filter) and `:504` (`check_declared_scope_reconciliation`, `unenumerated = [m for m in matches if m not in literal_declared]`)
- **Evidence:** The projection closure deliberately excludes patterns and delegates them to the
  reconciliation check; the reconciliation check can only report *matches the deliverable does not also
  enumerate*. A pattern that currently matches **zero** files therefore passes both. Executed against
  the live tree with a deliverable whose entire declared write surface is
  `**Files expected to mutate:** - src/newthing/*.py`:

  ```
  closure gaps: []  | pop_complete: True  | declared_scanned: 1
  recon  gaps: []  | globs_declared: 1, globs_expanded: 1, matches_enumerated: 0,
                     directories_matched: 0, population_complete: True
  ```

  The validator accepts the shape: `manage-solution-outline.py:377`'s wildcard rejection (check 3a)
  walks `affected_files` only, deliberately, and `_plan_parsing.py:503` puts the raw pattern into the
  write-set (`deliverable_write_set` returns `['src/newthing/*.py']`).
- **Why it matters:** The one deliverable class whose mutation set is least knowable at authoring time —
  the survey-scope class this plan exists to make checkable — is the one whose declared write surface
  the closure cannot constrain, and the result is published as `population_complete: True`. That is a
  measured-looking verdict over an unexamined scope, which is the module's own stated failure mode
  turned on itself. A `write-new` pattern is the natural way to hit it, since a not-yet-created file
  matches nothing.
- **Action:** Treat a declared glob that reaches the **write-set** (not merely the survey pool) as an
  unmeasured scope when it expands to zero matches: either report it as `unexpandable_glob` with a
  distinct cause ("a write-scope pattern that matches nothing cannot be reconciled"), or require the
  projection closure to demand at least one step target that `fnmatch`es the pattern. Prefer the
  second, because it is the property the deliverable actually owes: a declared sweep must be projected
  onto some task.
- **Done when:** a test declares `Files expected to mutate: src/newthing/*.py` on a deliverable with a
  task that targets nothing matching it, and the mechanical Q-Gate reports at least one finding (or
  `population_complete: False`); the same deliverable with a matching step target reports none.
- **Effort:** M
- **Risk if fixed:** Medium — could produce findings on existing outlines that legitimately declare a
  glob under `Files to survey:`; scope the new rule to the write-set fields so the read-only candidate
  pool is unaffected.

## G9 — Correct `phase-4-plan/SKILL.md`'s claim that only the error path clears `qgate_validation_required`

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md:1047`
- **Evidence:** "`qgate_validation_required` is `true` on every successful phase-4-plan completion
  (Step 8b signals unconditionally — both module-mapping and scope-criterion validators apply to every
  plan) and `false` **only on the unrecoverable error path**." The same file at `:936-950` defines two
  further paths to `false` — the `plan.phase-4-plan.q_gate_validation == off` opt-out (B1) and the
  surgical-scope bypass (B2) — and `:61`, a line **this diff edited**, names both explicitly. The stale
  sentence is pre-existing on `origin/main` (`git show 63943f5^:…` shows it at line 1030).
- **Why it matters:** It is the n−1 site of the exact claim D4 is about, inside a file the change
  edited, and it tells an implementer the bypass does not exist. A reader reaching Step 10's output
  contract before Step 8b gets the wrong contract.
- **Action:** Rewrite the sentence to match `:61` — `true` on every successful completion **except**
  when B1 or B2 forces it `false`, and `false` on the unrecoverable error path.
- **Done when:** `grep -n "only on the unrecoverable error path" marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md`
  returns nothing, and the surviving sentence names B1 and B2.
- **Effort:** S
- **Risk if fixed:** None.

## G10 — Widen `manage-lessons` component derivation to the survey pair (residue B3)

- **Kind:** omission
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/_lessons_query.py:145-164`, `_derive_components`
- **Evidence:** `for entry in deliverable.get('affected_files', []):` — the only field read. A
  survey-scope deliverable declaring no flat list contributes zero components and zero
  `unmapped_paths[]`. `manage-lessons/SKILL.md` step 3's promise that "narrowing is visible rather than
  silent" does not hold for it. Declared as an open bounded survivor in `report-02.md:570`; confirmed
  open.
- **Why it matters:** `manage-lessons consult` surfaces no lesson for the skills a survey-scope plan
  will actually edit, and the silence is indistinguishable from "no lesson applies".
- **Action:** Replace the direct field read with `deliverable_write_set(deliverable)` (or the full
  declared surface, if the intent is to surface lessons for read scopes too — state which and why).
- **Done when:** a test builds a deliverable declaring only `Files to survey:` / `Files expected to
  mutate:` and asserts `_derive_components` returns the component the mutation path maps to; reverting
  to `affected_files` turns it red.
- **Effort:** S
- **Risk if fixed:** Low — more lessons surface for survey-scope plans, which is the intent.

## G11 — Derive `test_the_finding_names_every_hit_and_states_the_true_total`'s precondition from the directory (residue B4)

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/manage-tasks/test_qgate_closure.py:696`
- **Evidence:** `assert len(hits) <= _closure._MAX_HITS_NAMED` where `hits` is the live expansion of
  `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/*.py`. Re-derived: 14 files today
  against a cap of 20, so six additions to that directory turn this into a hard failure of an unrelated
  change. Declared open with a `(b)` bound in `report-02.md:322`; confirmed open.
- **Why it matters:** A deterministic, loud false red on a change that has nothing to do with the
  closure — the cost lands on whoever next adds scripts to `manage-tasks`.
- **Action:** Either monkeypatch `_MAX_HITS_NAMED` above the live count for this test, or point the
  multi-hit glob at a fixture directory the test creates, so the property under test stops depending on
  the size of a production directory.
- **Done when:** the test passes with `_MAX_HITS_NAMED` set to any value at or below the live script
  count, and still fails under the `unenumerated[:1]` mutant.
- **Effort:** S
- **Risk if fixed:** None.

## G12 — Persist `scope_provenance` alongside `scope_estimate` (residue R1)

- **Kind:** omission
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py:994` (computed), `:1004` (only `scope_estimate` persisted), `:1019` (provenance used in the log line and discarded)
- **Evidence:** `references['scope_estimate'] = scope_estimate; write_json(references_path, references)`
  — `scope_provenance` never reaches the file. `grep -rn scope_provenance marketplace/bundles/**/scripts`
  finds no persistence site. The deep-lane refine Step 9 later overwrites `scope_estimate`, so on a
  deep-lane plan the router's own input is destroyed by its output, while a light-lane plan keeps it —
  the evidence survives exactly when nobody needs it. Sited at D0 and left unfixed by design
  (`actual-state.md:129`).
- **Why it matters:** Nothing can audit *whether the lane was right*; the routing checker audits which
  steps were pruned, which is a different question. Every retrospective that wants to grade the routing
  decision is reading a field the routing decision overwrote.
- **Action:** Write `references['scope_provenance'] = scope_provenance` in the same `write_json` call,
  and have the deep-lane Step 9 overwrite record its own provenance under a distinct key rather than
  replacing the pre-route one.
- **Done when:** after `scope-estimate-heuristic --persist`, `references.json` carries both fields, and
  a test asserts the pre-route provenance survives a simulated Step 9 overwrite of `scope_estimate`.
- **Effort:** M
- **Risk if fixed:** Low — an additive field; consumers reading `scope_estimate` are unaffected.

## G13 — Correct the thirteen sites naming phase-4-plan **Step 8b** as the execution-manifest composer (residue R3)

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** the thirteen instances are enumerated in place, so nothing is hidden inside an aggregate —
  they are one mechanical substitution across a closed, named list:
  1. `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md:251`
  2. `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md:443`
  3. `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md:747`
  4. `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/manifest-schema.md:5`
  5. `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md:108`
  6. `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md:713`
  7. `marketplace/bundles/plan-marshall/skills/extension-api/standards/extension-contract.md:412`
  8. `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:121`
  9. `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:420`
  10. `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1164`
  11. `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md:173`
  12. `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md:639`
  13. `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/workflow.md:134`
- **Evidence:** Each says the manifest is composed by / at `phase-4-plan` **Step 8b**. The canonical
  numbering is in `phase-4-plan/SKILL.md:61` and `:675` — **Step 7b** composes the execution manifest;
  Step 8b is the LLM Q-Gate dispatch signal. Re-derived count matches `report-02.md:569`'s 13 exactly
  (the grep returns 15; `phase-1-init/SKILL.md:907` names phase-1-init's own Step 8b and
  `phase-4-plan/SKILL.md:61` is correct).
- **Why it matters:** Thirteen documents send an implementer to the wrong step of the phase they are
  reading about, and one of them (`phase-5-execute/standards/workflow.md:134`) is the standard that
  explains why the manifest exists at all.
- **Action:** Substitute "Step 7b" at all thirteen sites in one `chore/` change; no code moves.
- **Done when:** `grep -rn "Step 8b" marketplace/ --include=*.md | grep -i manifest` returns only
  `phase-4-plan/SKILL.md:61` (which correctly distinguishes 7b from 8b).
- **Effort:** S
- **Risk if fixed:** None.

## G14 — Enforce survey-pair disjointness in the outline validator (residue R4)

- **Kind:** omission
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py:335-397`, `validate_deliverable_contract` check 3
- **Evidence:** The function reads `survey_scope` and `mutation_scope` only to decide whether *either*
  form of declaration is present (`:360-370`); it never compares the two lists.
  `outline-workflow-detail.md:822` states the requirement — "each file appears under **exactly one**
  field … the two lists are therefore disjoint by construction" — and the only trace of it in code is
  the defensive-dedupe comment at `_plan_parsing.py:477`. A stated invariant that nothing checks, which
  is the generalisation this plan's own Notes record.
- **Why it matters:** A path declared under both fields is counted as read by one heading's default and
  as a write by the other; consumers dedupe defensively, so the contradiction never surfaces to the
  author who can fix it.
- **Action:** Add a check 3c emitting `D{num}: path 'X' declared under both **Files to survey:** and
  **Files expected to mutate:** — the two lists are disjoint by construction`.
- **Done when:** a test declaring the same path under both fields produces exactly that error, and a
  correctly-authored disjoint pair produces none.
- **Effort:** S
- **Risk if fixed:** Low — could fail existing outlines that violate the rule; that is the point, but
  check the archived corpus before landing.

## G15 — Make `references.affected_files` carry the survey pair, or make its four consumers read the write-set (residue R5)

- **Kind:** omission
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** the writer is `plan-marshall/workflow/q-gate-validation.md` § Step 7; the consumers are
  `manage-status/scripts/_cmd_classification_validate.py:128`,
  `manage-status/scripts/_cmd_sibling_collision.py:125`,
  `manage-metrics/scripts/manage-metrics.py:2630`, and
  `phase-5-execute/scripts/scope_creep_check.py:69`
- **Evidence:** `phase-4-plan/SKILL.md:688` carries the ⚠ this run added: "`references.affected_files`
  … does **not** currently carry a survey-scope deliverable's `Files expected to mutate:` paths, so
  this figure can understate the declared surface." The field is still written from the flat list, and
  four scripts read it. (`scope_creep_check.py` is partly protected — it also unions every `TASK-*.json`
  step target — but classification-validate, sibling-collision and metrics are not.)
- **Why it matters:** A survey-scope plan's whole mutation surface is invisible to classification
  validation, sibling-collision detection and the metrics denominator. This is the same
  incomplete-derived-set failure the plan closed at the Q-Gate, still open one layer up: the omission is
  precisely what never entered the field, so nothing downstream can see it.
- **Action:** Widen the § Step 7 writer to the deduplicated union of `affected_files` +
  `mutation_scope` (the `deliverable_write_set` definition), and state at the field's schema that it is
  the write-set rather than the flat list. If widening the field is too broad a change, convert the
  three unprotected consumers to derive from `manage-solution-outline list-deliverables` instead.
- **Done when:** for a plan whose only deliverable is survey-scope, `manage-references get --field
  affected_files` returns its `Files expected to mutate:` paths, and a test pins that.
- **Effort:** M
- **Risk if fixed:** Medium — `affected_files_count` feeds the B2 surgical bypass predicate and the
  scope bands, so widening the field changes routing for survey-scope plans. That is the intended
  direction (`phase-4-plan/SKILL.md:940` says reading the flat list alone makes the bypass fire more
  readily on exactly these plans), but it must land with the bypass documentation in one change.

## G16 — Normalize paths before deduplicating in `deliverable_write_set`

- **Kind:** bug
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py:510` (the `path not in seen` test) against the docstring claim at `:477-479`
- **Evidence:** The docstring states "a path declared under both fields contributes **one** write-set
  member". Executed:

  ```
  {'affected_files': [{'path': './src/a.py', 'intent': 'write-replace'}],
   'mutation_scope':  [{'path': 'src/a.py',   'intent': None}]}
  → ['./src/a.py', 'src/a.py']
  ```

  Two members. The byte-identical case correctly yields one. `_qgate_closure.normalize_declared_path`
  (`:101`) exists precisely because these two spellings name the same file.
- **Why it matters:** The closure re-normalises, so its own verdict is unaffected — but every other
  `deliverable_write_set` consumer (file-type bucket adjudication, the `module_testing` profile check,
  the phase-6 foreign gate, any cardinality derived from the write-set) sees a phantom extra member.
  The docstring asserts a property the code does not have.
- **Action:** Deduplicate on the normalized spelling — either import `normalize_declared_path` or lift
  it into `_plan_parsing` and have `_qgate_closure` import it from there (it is the more natural owner,
  since it is where declared paths are parsed).
- **Done when:** a test declaring `./src/a.py` and `src/a.py` under the two fields asserts a one-member
  write-set, and the docstring's claim holds; removing the normalization turns it red.
- **Effort:** S
- **Risk if fixed:** Low — write-sets shrink only where they currently double-count.

## G17 — Codify the characterization-corpus rule that D5 applied but never wrote down

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** the rule has no home. It exists only as `report-01.md:242-267` (a run record) and a
  rationale comment at `test/plan-marshall/manage-tasks/test_manage_tasks_qgate_mechanical.py:28-34`
- **Evidence:** `plan.md` D5 requires "a **characterization-corpus rule**: a fixture corpus is
  population-derived from the live corpus directory — enumerate every fixture, then justify each
  **exclusion** explicitly. ⛔ Opt-out with a stated reason, never opt-in by selection". The run applied
  it to one corpus, and applied it well (three exclusions stated with reasons; the corpus aligned
  rather than exempted; `_ALL_CHECKS` cross-checked against the live key set at `:196`). But
  `grep -rn "characterization" marketplace/bundles --include=*.md -il` returns one unrelated file
  (`manage-solution-outline/examples/refactoring.md`), so no skill or standard states the rule.
- **Why it matters:** The plan's own § "sub-classes" says it: "⛔ **And prose warnings are NOT a
  control.**" A rule that lives in a dated run report binds nobody. The next characterization corpus
  gets selected rather than enumerated, and an under-enumerated corpus silently pins the defect as
  expected behaviour — which is what this corpus was doing before the run fixed it.
- **Action:** Add the rule to `pm-dev-python:pytest-testing` (or to `plan-marshall:ref-code-quality`,
  whichever owns fixture discipline): a fixture corpus is enumerated from the live corpus directory,
  every excluded fixture carries a stated reason, and the asserted name set is cross-checked against the
  produced set rather than hard-coded. Cite this plan's corpus as the worked example.
- **Done when:** the rule appears in a skill or standard under `marketplace/bundles/`, and
  `plugin-doctor`'s rule catalogue or a test references it, so it is discoverable without reading
  `report-01.md`.
- **Effort:** M
- **Risk if fixed:** None.

## G18 — Record the plan's unmet verification clause where the plan, not only the report, will be read

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/350-outline-derived-set-closure-integrity/plan.md:166` (§ Verification, "Each fixture carries the pre-fix text verbatim") vs `report-01.md:275-286`
- **Evidence:** The run states plainly that this clause is "**Not satisfied as literally written,
  deliberately**", because nothing shipped is a content detector — all three closures are set
  computations — and substitutes the mutation campaign, which is strictly stronger. The disposition is
  honest and correct. But it lives only in the run report, so a later reader of `plan.md` sees an
  unqualified verification requirement.
- **Why it matters:** A deliverable satisfied by a different mechanism than specified is a deviation
  even when the alternative is better; the deviation should be findable from the contract, not only
  from the record of one execution.
- **Action:** Nothing to build. When this plan's lesson is folded, carry the distinction forward: the
  predicate axis of a *set* detector is exercised by mutation, not by a verbatim negative fixture — a
  verbatim fixture applies only to content detectors.
- **Done when:** the distinction appears wherever the "every set-guarding detector must be
  population-derived" rule is stated, so a future plan does not write an inapplicable verification
  clause.
- **Effort:** S
- **Risk if fixed:** None.

## G19 — Re-anchor the eleven unresolvable commit SHAs quoted across the three documents

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** every citation site, re-derived by grepping the eleven SHAs across the three documents —
  `report-01.md:73, 331`; `report-02.md:99, 110, 134, 135, 169, 222, 355, 356, 401, 423, 453, 458`;
  `actual-state.md:4, 168`
- **Evidence:** `git cat-file -t` reports MISSING for every one of `3b57b7e`, `9d257dd`, `4ec39fd`,
  `51829af`, `4f7ab38`, `f11e8b7`, `8486214`, `117d351`, `f2a7cd9`, `501ce21`, `d898934`. Branch
  `claude/derived-set-closure-integrity-3i53aj` is absent from `git branch -r`; the PR was squash-merged
  as `63943f5`. Run 01's original branch `origin/claude/derived-set-closure-integrity-g7n8x2` does still
  exist, so the *pre-rebase* SHAs remain resolvable.
- **Why it matters:** `report-02.md` § Proposal 1 identifies exactly this hazard ("a rebase falsifies
  every commit SHA the prior run's report quotes") and then corrected the documents **to the rebased
  SHAs**, which a squash merge deleted. Every commit citation in the landed record is now unresolvable,
  including the ones G2 and G3 need.
- **Action:** Re-anchor each citation to something durable: the squash-merge commit `63943f5` for
  landed content, and the surviving `g7n8x2` SHAs (with the branch named) for run 01's history. Fold
  the lesson into Proposal 1 — a rebased SHA is durable only until the branch is deleted, so a report
  should quote a ref plus a SHA, or the merge commit.
- **Done when:** every commit reference in the three documents resolves with `git cat-file -t` in a
  fresh clone of `main`, or names the branch it lives on.
- **Effort:** M
- **Risk if fixed:** None.
