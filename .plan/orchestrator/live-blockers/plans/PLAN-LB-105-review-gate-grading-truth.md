# PLAN-LB-105: The review gate grades what the branch really did and every criterion the outline wrote

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-105-review-gate-grading-truth.md` and is queued as one row file, `queue/PLAN-LB-105.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's instruction of 2026-11-02 ("stage the corresponding plans, aggregate where sensible") from three
> consumer-repo findings that `lessons-routing` routed here. All three come from API-Sheriff, a Maven project, and all are
> graded **high**:
> - `lessons-routing-064`: the `weakened_test` check (five plans, five PRs).
> - `lessons-routing-065`: the success-criteria parser (two PRs).
> - `lessons-routing-058` item 1: outline assessment coverage. This item no longer occurs at HEAD and is not a deliverable here
>   (see Claim Labels).
>
> **It also absorbs PLAN-LB-75 D3** (test-integrity reach: no-worktree plans, qualified names, the rubric conflict). That
> deliverable builds the same matcher in the same function, and LB-75 D3 now points here. Every claim was re-checked at
> `0fb6a79b1`.
>
> **Each deliverable is its own outline deliverable, and each Done-when is its own success criterion. Do not merge them.** A
> Done-when says "fails at `0fb6a79b1`" only where the behaviour is new. A clause that already holds says "holds at
> `0fb6a79b1`" and is kept as a control.

## Objective

The finalize functional review blocks unattended finalize for two reasons that have nothing to do with the plan's work:

- **The test-integrity check misreads test changes.** It reads a moved, renamed, split or deliberately removed test as lost
  assertions. It compares against the base tip instead of the merge base. It raises the same rows again at every head after an
  operator has accepted them, and it is silent for every plan without a worktree.
- **The success-criteria parser freezes only part of a list.** It keeps only the first line of a wrapped or nested criteria
  list, so the review grades part of a deliverable without saying so.

This plan fixes both:

- A genuine loss stays blocking.
- A removal that was decided on is decided once.
- A resolved finding that is observed again has one visible outcome, both in the store and in the review.
- Every criterion the outline wrote is frozen and graded.

## Deliverables

1. **A moved, renamed or split test is not a lost assertion, the pre-image is the merge base, and every plan is graded.**
   - `changed_files` stops discarding renames. The check pairs each deleted test path with the test paths the branch added or
     renamed, and compares assertion totals across the whole changed test set rather than per path.
   - A loss is reported in exactly three cases. The per-path report stays the unit of the finding row.
     - The total for the set drops.
     - A named test disappears from every after-file. A test is named by an identity that does not depend on its path: class
       plus function, with `async def` and indented methods included.
     - One test's count drops while that test still exists. This includes a deleted test whose assertions were added to another
       test in the same file.
   - `_pre_image` reads the file at `git merge-base {base} HEAD`, not at `{base}`, so the changed set and the pre-image describe
     the same tree.
   - (From LB-75 D3) A plan with `use_worktree: false` is graded against the main checkout's diff to the base instead of being
     skipped (`worktree_unresolved`). The choice of evidence root is recorded at outline.
   - The module docstring and `functional-review.md` § 3e state the new rule exactly: what counts as a move, what is still
     caught, and what is not caught (a weaker replacement assertion, for example).

   *Done when:* each of these fails at `0fb6a79b1`:
   - a fixture branch that `git mv`s an unchanged Python test file yields no `assertion_removed` row;
   - a fixture branch that splits one test file into two, carrying over every test and assertion, yields none;
   - a fixture branch that moves an unchanged **Java** test class yields none. The check counts at file level only, with no
     per-function leg, and the consumer that saw this runs Maven;
   - a fixture yields no row where `origin/main` gains an assertion in a test file after the branch point and the branch never
     touches that file;
   - an assertion moved between two methods of one class is reported;
   - an `async def` test that loses an assertion is reported;
   - a deleted test whose assertions are added in equal number to another test in the same file is reported;
   - a `use_worktree: false` fixture plan that removes an assertion yields a `weakened_test` finding.

   And these **hold at** `0fb6a79b1` and are kept as controls:
   - a wholly deleted test file whose tests appear nowhere else is reported;
   - an assertion removed from a test that keeps its name is reported;
   - an assertion moved to a NEW test function is reported;
   - a skip marker added to a test is reported as `test_filtered`.

2. **A removal that was decided on is decided once, by test identity rather than by head.**
   - An accepted removal set is recorded in the plan's status record, keyed by the D1 test identity plus the number of removed
     assertions. It has two sources:
     - an outline deliverable that declares the tests it removes. The field name is decided at outline, and the field is parsed
       through `_plan_parsing`, the one deliverable parser;
     - `manage-status loop-back close --accept` on a `weakened_test` finding, which records the identities that finding
       removed, not only the closing head.
   - `_grade_test_integrity` raises no `weakened_test` row when every removed identity is in the accepted set. It lists those
     identities in the payload as `accepted_removals`, so they stay visible. A row whose removed set grows or changes is raised
     again; an unchanged set is not asked about again at a later head.
   - The new status key is written only by the verb that owns it, and it joins `PROTECTED_STATUS_METADATA_KEYS`, exactly as
     `functional_review_override_heads` does.
   - (From LB-75 D3) `functional-review.md` § 3e and `review-rubric.md` give one answer to "the deliverable asked for this
     removal": a declared removal is accepted, and an undeclared one blocks until an operator accepts it.

   *Done when:* each of these fails at `0fb6a79b1`:
   - after an operator close accepts a removed test at head A, a validate at head B (a later fix commit, same removed set)
     carries no blocking `weakened_test` finding and lists the removal under `accepted_removals`;
   - an outline that declares the removal of test `T` yields no blocking row for the deletion of `T`;
   - a doc test asserts that § 3e and `review-rubric.md` state the declared-removal rule identically;
   - a guard test asserts that the new key is in `PROTECTED_STATUS_METADATA_KEYS` and that a generic `metadata --set` on it is
     refused.

   And this **holds at** `0fb6a79b1`: an undeclared, unaccepted removal is a blocking `weakened_test`. It still is after this
   plan, at every head. A second removed test at head B is raised even though the first was accepted.

3. **A resolved blocking finding that is observed again unchanged has one visible outcome, in the store and in the review.**
   - **At HEAD,** an operator cannot accept such a finding:
     - A full loop-back round first resolves every earlier `functional-review` finding as `taken_into_account`, then re-files
       what still blocks.
     - A re-filed finding with the same title, detail and rule matches the resolved record. `qgate add` returns `kept` and
       leaves the resolution at `taken_into_account`.
     - The finding still blocks in `validate`, but it is not pending in the store, so `loop-back close --accept {hash}`
       refuses it with `finding_not_pending`.
     - `--reopen` re-arms only a `fixed` record and returns `kept` for every other resolution.
   - **After this plan,** a finding that the review re-files as still blocking is pending in the store after Branch B, through
     an explicit, documented verb outcome.
   - `--reopen` on a record it does not re-arm returns a named field saying why (for example `not_reopened: <resolution>`),
     never a bare `kept` that a caller cannot tell apart from a no-op.
   - An observation alone does not re-arm an operator-`accepted` record.
   - `functional-review.md` Branch B reads a `qgate add` return through the `QGATE_PERSIST_OK` partition, not as "any
     non-`success` return halts".

   *Done when:* each of these fails at `0fb6a79b1`:
   - a test files a blocking finding, runs the Branch B `resolve-by-rule`, then re-adds the identical finding with the
     workflow's exact flags. It finds the finding in `qgate list --resolution pending`, and `loop-back close --accept {hash}`
     succeeds;
   - `qgate add --reopen` against a `taken_into_account` record returns the named not-reopened outcome;
   - a doc test asserts that Branch B names `QGATE_PERSIST_OK`, or its four values.

   And this **holds at** `0fb6a79b1`: an identical re-add against a pending record returns `deduplicated`, and an
   operator-`accepted` record stays `accepted` after an identical re-add.

4. **The success-criteria parser keeps every criterion and reports what it could not read.**
   - `outline_deliverables` reads each top-level bullet of the `**Success Criteria:**` block as one criterion, together with its
     continuation lines and nested sub-bullets.
     - It accepts `-` and `*` bullets, and a blank line between bullets.
     - A line inside the block that is neither a bullet nor part of one is returned as `unparsed`, never dropped.
     - It stays the only success-criteria parser in the tree.
   - `snapshot-criteria` returns a criterion count per deliverable and the `unparsed` lines, beside the total `criterion_count`
     it already returns. `review_support validate` reports the frozen count per deliverable.
   - **Migration:** a plan frozen with the old parser must not turn into `criterion_rewritten` drift just because the new
     parser reads its wrapped bullet in full.
     - A frozen criterion that is a prefix of a newly parsed one is reported as a named state (for example `parser_extended`),
       not as drift.
     - A re-freeze still needs `criteria-refreeze-authorize`, and nothing re-freezes automatically.
   - `manage-solution-outline/templates/deliverable-template.md` states the bullet shapes the parser accepts.

   *Done when:* each of these fails at `0fb6a79b1`:
   - an outline deliverable has three criteria: one wrapped over two lines, one with an indented sub-bullet, and one `*` bullet.
     It freezes three criteria with their full text (HEAD freezes one, first line only);
   - sealing a verdict that grades `C2` and `C3` by `criterion_id` succeeds (HEAD refuses with `unknown_criterion_id`);
   - `snapshot-criteria` returns a stray non-bullet line inside the block as `unparsed`;
   - an old-parser snapshot of a wrapped bullet, validated after the parser change, yields `parser_extended` and no
     `criterion_rewritten` finding.

   And this **holds at** `0fb6a79b1`: an outline whose criteria are all single-line `- ` bullets freezes a byte-identical
   snapshot before and after the change.

Split guard: four deliverables on one theme, that the review gate grades the truth.
- D1 to D3 are one pipeline for the same `weakened_test` row: the detector, the decision record, and the outcome in the store.
  D3 is what makes D2's `--accept` reachable.
- D4 is the parser that feeds the criteria half of the same gate.
- Each deliverable could ship alone. Together they remove the operator close that every review round needs today.
- A fifth deliverable for 058 item 1 was dropped because that symptom no longer occurs at HEAD.

## Standing Constraints

- **The gate gets more precise, never more permissive.** Every relaxation (D1 moves, D2 acceptances, D4 migration state) ships
  with a control showing that a genuine loss or an unmet criterion still blocks.
- **One identity scheme for a test**, defined once in D1 and used by D2's accepted set. No second matcher.
- **One success-criteria parser** (`outline_deliverables`), with no copy in `phase-6-finalize`.
- **No automatic re-freeze of any snapshot.** A frozen snapshot is migrated only through the existing authorize path.
- **Protected keys.** Every new status-record key written by an owning verb joins `PROTECTED_STATUS_METADATA_KEYS`.
- **Decisions go to scripts, not prose.** Workflow prose changes in `functional-review.md` route each decision to a script
  outcome a test can pin, not to prose a model must interpret. This keeps the runbook usable across the whole fleet (claude,
  opencode, antigravity).
- **Non-Python fixtures.** Fixtures cover a non-Python test file wherever the consumer evidence is Java (D1).
- **No Sonar.** Sonar is not enabled for this project and is ignored: collect no Sonar figure and require none.

## Claim Labels

- OBSERVED: rename detection is off, and the changed set uses a three-dot diff — `phase-6-finalize/scripts/_review_support_integrity.py` L73-78 § `changed_files` (`git diff --name-only --no-renames {base_ref}...HEAD`).
- OBSERVED: the pre-image is read at the base ref itself, not at the merge base — `_review_support_integrity.py` L81-84 § `_pre_image` (`git show {base_ref}:{path}`). The base resolves to `origin/{base_branch}` when that ref exists — `manage-references/scripts/_references_core.py` L243-261 § `resolve_base_ref`.
- OBSERVED: a deleted test file counts every assertion as gone, a file the branch adds is skipped, and counting is per path, with no total across files — `_review_support_integrity.py` L157-169 § `compute_test_integrity`.
- OBSERVED: per-function keys are bare names, taken only from column-0 `def` or JS `it/test/describe` — `_review_support_integrity.py` L105-121 § `_FUNCTION_HEADER_RE`, `_function_assertion_counts`.
- OBSERVED: the after-image is the file on disk in the worktree, not `HEAD:{path}` — `_review_support_integrity.py` L160-166. This is adjacent only; D1 states whether it stays that way.
- OBSERVED: `worktree_unresolved` is skipped silently for every `use_worktree: false` plan — `review_support.py` L213-214; `_references_core.py` L294-296 (carried from PLAN-LB-75; re-check the lines at outline).
- OBSERVED: every test-integrity row is a blocking `weakened_test`, and no acceptance input is consulted — `phase-6-finalize/scripts/review_support.py` L205-238 § `_grade_test_integrity`.
- OBSERVED: the only lasting record of an operator close is the list of heads, and accepted findings are resolved in the Q-Gate store — `manage-status/scripts/_cmd_loop_back.py` L323-368 § `_record_override_head`, L549-553 (`resolve_qgate_finding ... 'accepted'`).
- OBSERVED: `--accept` refuses any hash that is not pending — `_cmd_loop_back.py` L491-510 (`finding_not_pending`).
- OBSERVED: a full loop-back round resolves the earlier findings, then re-files them — `phase-6-finalize/workflow/functional-review.md` L546-553 (`resolve-by-rule ... taken_into_account`), L557-564 (`qgate add ... --rule functional-review`), and L585 ("On a non-`success` return from any `qgate add` ... halt").
- OBSERVED: an identical title plus discriminator against a resolved record returns `kept` with the resolution unchanged, and `reopen` re-arms only `fixed` — `manage-findings/scripts/_findings_core.py` L1520-1591 § `add_qgate_finding`. The partition `QGATE_PERSIST_OK` is at L83-94.
- OBSERVED: the § 3e text says the finding "stands until the assertion is restored or an operator override closes the step" — `functional-review.md` L301. PLAN-LB-75 cited this passage as L309; it has moved.
- OBSERVED: no outline field declares a planned test removal — `architecture search --content` for `planned[_ -]removal|removed_tests|Tests to remove|test_removal` returned `count: 0` over `files_scanned: 3686`, with `unreadable: 0`, `elided: 0` and `truncated: false`.
- OBSERVED: `_SUCCESS_CRITERIA_RE` captures only an unbroken run of lines that start with `- `, and the parser keeps only lines that start with `- ` — `manage-solution-outline/scripts/_criteria_snapshot.py` L72 and L653-671 § `outline_deliverables`. It is the only parser, and `_review_support_attribution.py` calls it.
- OBSERVED: `criteria_drift` compares the frozen rows with the same parser's live output, so a criterion that both drop is never reported as drift — `_criteria_snapshot.py` L977-1028. A frozen prefix compared with a fuller live text reads as `rewritten` (L1015-1017), which is the D4 migration hazard.
- OBSERVED: `snapshot-criteria` already returns a total `criterion_count`, but no count per deliverable and nothing unparsed — `_criteria_snapshot.py` L954-963. This partly refutes 065's request to print the parsed count: the total exists, and what is missing is the per-deliverable count and an unparsed report.
- OBSERVED: `unknown_criterion_id` is refused against the frozen count per deliverable — `review_support.py` L340-378, L397-411.
- OBSERVED (058 item 1, refuted at HEAD): with an empty assessment store, the coverage check reports `not run` and flags no deliverable — `plan-marshall/workflow/q-gate-validation.md` L257-278. This landed in `8442a5e33` (#1773, PLAN-LB-42, 2026-10-15), after the sighting (lesson `2026-10-12-16-001`). `6953df489` (#1788) shipped its deliverable 2 as domain narrowing and touched no assessment writer.
- HYPOTHESIS: a mixed-domain plan in which only plugin files are assessed has a non-empty store, so every affected file outside the plugin domain is flagged as missing coverage. The only assessment writers are `pm-plugin-development:ext-outline-workflow` (`phase-3-outline/standards/component-analysis-contract.md` L14-16) and the re-entry backfill (`phase-3-outline/standards/outline-workflow-detail.md` L30-42), and the check flags every uncovered file when the store is non-empty (`q-gate-validation.md` L270-273). Not sighted; recorded as an epic watch, not a deliverable.
- HYPOTHESIS: in some runs, Branch B's rule that any non-`success` return halts reads `kept` as a halt — confirm against `functional-review.md` L585 and a recorded run (verify-at-outline).
- HYPOTHESIS: the CLI flag `qgate add --reopen` is declared in `manage-findings/scripts/manage-findings.py` and passes straight to `add_qgate_finding(reopen=...)` — confirm the flag and its help text (verify-at-outline).
- HYPOTHESIS: `review-rubric.md` still says that a deliverable asking for the change justifies a weakened test — confirm at `phase-6-finalize/standards/review-rubric.md` § 2 (verify-at-outline; PLAN-LB-75 records the same claim).
- HYPOTHESIS: for a plan without a worktree, the right evidence root is the main checkout's diff to `origin/main` — confirm at `review_support.py` § evidence root and `_references_core.py` § `resolve_live_worktree` (verify-at-outline).
- Verify-first clause (D1): before editing, reproduce the #502/#505 shape with a git-mv fixture at HEAD and confirm one full-loss row per old path. If it does not reproduce, the cause is elsewhere: loop back and re-scope. Decide the qualified-name scheme (module path plus class plus function) and record why.
- Verify-first clause (D4): before the parser change is committed, decide the name of the migration state and prove on a fixture that no in-flight snapshot turns into drift.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_review_support_integrity.py` — `changed_files`, `_pre_image`, `compute_test_integrity`, the identity key, the docstring (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_support.py` — `_grade_test_integrity`, the evidence root, the `accepted_removals` payload, the per-deliverable criterion count in `validate` (D1, D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_loop_back.py` — `cmd_loop_back_close` records the accepted identities (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py` — `_SUCCESS_CRITERIA_RE`, `outline_deliverables`, `criteria_drift` migration state, `PROTECTED_STATUS_METADATA_KEYS` (D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — `add_qgate_finding` re-observation outcome (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/manage-findings.py` — `qgate add --reopen` output (D3; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py` — evidence root for a plan without a worktree (D1; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py` — the declared-removal field (D2; verify-at-outline, field name decided there)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py` — `snapshot-criteria` output fields (D4; verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/templates/deliverable-template.md` — accepted bullet shapes, declared removals (D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md` — § 3e (L301), Branch B (L546-585) (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md` — the declared-removal rule (D2)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_weakened_test_d4.py` — move, split, Java and merge-base fixtures (D1)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_criteria_parsing_d2.py` — multi-line bullet and migration fixtures (D4)
- OBSERVED: `test/plan-marshall/phase-6-finalize/` — acceptance and doc tests (D1, D2, D3)
- OBSERVED: `test/plan-marshall/manage-findings/` — re-observation outcome tests (D3)
- OBSERVED: `test/plan-marshall/manage-status/` — `loop-back close` and protected-key tests (D2)
- OBSERVED: `test/plan-marshall/manage-solution-outline/` — parser and `snapshot-criteria` tests (D4)

## Dependencies and Sequencing

- **Depends on:** none.
- **Overlaps with PLAN-LB-75** (parked, WS-03), which is reshaped in the same act:
  - **LB-75 D3 is absorbed here** (into D1 and D2) and now points to this plan. Building one matcher twice, in two plans, would
    collide in the same function.
  - **LB-75 D1** (`run_open_criteria` exemptions, `criteria_gate` persisted) shares `review_support.py`, but touches a
    different symbol. Sequence the two plans; do not absorb D1.
  - **LB-75 D4** (override heads scoped to their head, `superseded_by` validated) shares `_criteria_snapshot.py`. The symbols
    differ (`_review_closed_reason` there, the parser and the protected-key tuple here), but both plans read
    `functional_review_override_heads`. Sequence the two plans; do not absorb D4.
  - **LB-75 D2** (re-freeze routing in phase-3-outline) does not overlap.
  - **Order:** emit this plan first. It is high severity, and LB-75 is medium and parked. Re-ground LB-75 against this plan's
    line moves before it runs.
- **Overlaps with PLAN-LB-107** (staged 2026-11-02) on `phase-6-finalize/` and `manage-status/`, and **with PLAN-LB-106** on the
  `test/plan-marshall/manage-findings/` directory. The gate decides each pairing.
- **Adjacent to:**
  - The other block regexes in `_plan_parsing.py` (`**Metadata:**` L320, `**Affected files:**` L462, `**Verification:**`
    L832). They use the same `(?:- [^\n]+\n?)+` shape and drop wrapped bullets the same way. They stay untouched here, and are
    recorded as a candidate finding for the epic.
  - The outline Q-Gate assessment coverage (058 item 1): no longer occurs at HEAD. The mixed-domain hypothesis is an epic
    watch.
  - Bot findings from `automatic-review` share `qgate add` but use their own rule keys. D3 changes no bot path.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-105-review-gate-grading-truth.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
