# PLAN-LB-118: The test-integrity gate decides a loss per identity, an accepted removal is exactly what was accepted, and a re-file does not re-arm an operator decision

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-118-review-gate-grading-fix.md` and is queued as one row file, `queue/PLAN-LB-118.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word ("Don't we have a single fix plan yet? If not, create") after the three-layer analysis of the landing of
> PLAN-LB-105 (PR 1913, merge `ce29d4b1f`). The report is `landings/PLAN-LB-105.md`; every finding id below (L1-n, L2-n, L3-n) is that
> report's. The points the orchestrator re-read at their lines are labelled OBSERVED; the points the analysis leaf read and the
> orchestrator did not re-read, and every claim about reach, are labelled HYPOTHESIS and are settled first.
>
> Ruling check. This is a fix plan for the finalize review gate that PLAN-LB-105 made: its done-condition in the epic vision is "the
> review gate can be trusted to mean what it says". D1 to D3 are graded blocking (a gate that passes a lost assertion, a gate row nobody
> can accept, a re-arm of an operator decision). D4 and D5 are minor to medium and separable. No token or measurement work.

## Objective

The test-integrity check that PLAN-LB-105 shipped reads the branch as one test set. Three of its decisions are wrong against its own
documents and against the spec's constraint "the gate gets more precise, never more permissive": the survival test pools a test name
over every changed file, a moved test function can still produce a row no one can accept, and a declaration without a count accepts any
count. The re-observation rule re-arms every `taken_into_account` record, including an operator's Hold. The `use_worktree: false` path
trusts whatever the main checkout holds, and a git timeout crashes `validate`.

After this plan a loss is decided per identity against what the same identity carried before, a moved test is not a loss and a loss is
always acceptable, an accepted removal covers exactly what was accepted, a re-file re-arms only what the review itself superseded, and
the evidence root and the git calls fail closed.

## Deliverables

1. **A loss is decided per identity, a moved test is not a loss, and every row can be decided.**
   - The survival test no longer lets an identity that already existed in another changed file absorb a loss
     (`_review_support_integrity.py:411-430,467-471`, L3-1): an identity survives only to the extent that the after-set carries MORE of
     it than the before-set already carried outside the deleted or modified path. The comparison is stated once in the module docstring
     and § 3e.
   - A test function moved from a surviving file to another file, or a split that keeps the original file, is not a loss
     (`:461-473`, L3-2): the per-path total drop is reported only when no identity accounts for it. The fourth loss case the docs do not
     name is either removed or named in the docstring and § 3e, whichever the outline decides; the decision is recorded.
   - Every row carries an identity or an explicit path-level key the close can record, so no row is unacceptable by construction
     (`:492-504`, `review_support.py:249`, L3-5 and L3-10): the set-total row is attributed to the file that lost the assertions, and a
     row without an identity is acceptable by path plus count.
   - The class scope stack does not pop on a column-0 comment or a dedented string inside a class body, and a nested class keeps its
     full path (`:270-282`, L3-11); an indented JS skip marker is attributed to its own test (`:605-617`, L3-12).

   *Done when:* each of these fails at `ce29d4b1f`: a fixture deleting a file with `test_x` while a modified file already carries
   `test_x` and the branch adds assertions elsewhere yields a row; a fixture moving a function from a surviving file to a new file yields
   no row; a fixture for each remaining row kind can be accepted by a close and is then not raised again at the next head; a class body
   with a column-0 comment keeps its method identities; `A.Inner::m` and `B.Inner::m` do not collide; an indented `it.skip(` on a test
   beside an already-skipped test is reported. Existing controls stay green: a wholly deleted file, a named-test removal, a move to a
   new test and a skip marker each still yield a row.

2. **An accepted removal is exactly what was accepted.**
   - A declaration without a count accepts nothing beyond what it names: the count becomes required, or a count-less entry accepts the
     identity only for a removal and never for a drop of a surviving test (`review_support.py:258-274`, L2-1). The spec's key stays
     identity plus count; the outline decides which.
   - The identities an operator close records come from the finding the operator saw: the close reads them from the validated head,
     and an attempt to close at a different head is refused or re-validated (`_cmd_loop_back.py:441-458`, L3-6).
   - The close keeps every row of a path, not the last (`:444`, L3-6): a path that both loses assertions and gains a skip marker records
     the identities of the loss.
   - `functional-review.md` § 3e, `review-rubric.md` and the module docstring state the same rule (D1 and D2 together): the cases
     named, the key, and which rows can be declared (L3-16).

   *Done when:* a count-less declaration for `test_x` does not accept a drop of a surviving `test_x` or a removal of more
   assertions than it named (red at base); a close at a head that differs from the validated one does not record a later removal; a
   file with an assertion loss and an added skip marker records the loss identities on close and is not raised again at the next head;
   a doc test pins the three texts to one statement of the cases and the key.

3. **A re-file re-arms what the review superseded, never an operator decision.**
   - The `taken_into_account` re-arm is scoped to the records a loop-back round itself resolved (by rule or source, decided at
     outline), so an operator's Hold in triage stays resolved (`_findings_core.py:1615`, L1-1 and L3-4). `rejected` and `accepted` keep
     their protection.
   - The comment at `:1641-1642`, `manage-findings/SKILL.md:262-267`, the `--reopen` help text and `functional-review.md:587` state the
     scoped rule and no longer say "not an operator decision" of the whole resolution (L1-1).
   - `--reopen` against a `taken_into_account` record returns the named outcome and does not re-arm LESS than a plain re-add; the
     semantics are stated once (L1-4).

   *Done when:* a fixture whose record was resolved `taken_into_account` by a triage Hold is `kept` on an identical re-file (red at
   base); a fixture resolved by the loop-back rule is `reopened` (holds at base); the doc test of the partition still passes; the
   decision on `--reopen` is pinned by a test.

4. **The evidence root and the git calls fail closed.** *(separable)*
   - A `use_worktree: false` plan is graded only when the main checkout's HEAD is the plan's branch and the tree is clean; otherwise
     `evidence_root_unresolved` or a named state, never success with zero rows (`_review_support_integrity.py:119-130,324-327`, L3-3).
   - `merge_base`, `_show` and every `_git` call return a TOON error on a timeout instead of raising (`:114,181,190,372-376`, L3-7);
     a failed `git show` is not read as "did not exist", and paths are read in a form that does not depend on `core.quotePath`
     (`:141-153,188-191`, L3-8); a missing merge base is a named state, not a silent fall back to the base tip (`:218-221,376`, L3-9).
   - The after-image documents what it covers: a committed removal restored only in the working tree is not a pass (`:194-210`, L3-13),
     or the docstring says what the working-tree-first read does not guarantee.

   *Done when:* a fixture with the main checkout on `main` for a no-worktree plan does not return success with zero rows (red at base); a
   timeout fixture returns `test_integrity_not_run`; a non-ASCII deleted test path is read; a missing merge base is reported by name.

5. **The parser reports what it could not read, and the documents state the current behaviour.** *(separable)*
   - A bold-field line indented under a criterion does not end the block silently, and a `- ` line inside a fenced block is not a
     criterion (`_criteria_snapshot.py:802-824`, L3-14); what the parser cannot read is listed as `unparsed`.
   - The retired-parser replay matches the retired rule on prose before the first bullet (`:855-879`, L3-15), and a continuation-line
     or sub-bullet append is not hidden as advisory when the frozen snapshot was written by the new parser (`:1265-1273`, L2-4); the
     discriminator the spec of PLAN-LB-105 did not ask for is decided here (L1-3).
   - Transitional wording and plan ids in current-state text are rewritten: `review-rubric.md:42`, `_criteria_snapshot.py:791-793`,
     `_review_support_integrity.py:99-101,160,176-179,422-425`, `_review_support_validate.py:467,476`, `_plan_parsing.py:812` (L3-17); the
     duplicated `main_checkout_root` and the two `_evidence_root` functions are consolidated or cross-referenced (L3-18).

   *Done when:* a fixture with an indented `**Given:**` under a criterion keeps the later criteria or lists them as `unparsed`; a
   continuation-line append to a frozen criterion is reported by a named state the gate does not treat as clean; a read of each cited
   line shows the wording corrected.

Split guard: five deliverables on one gate. D1 and D2 share the row shape and must be delivered together; D3 is independent; D4 and
D5 are the first to split off. A split runs in sequence, since D1, D2 and D4 edit one module.

## Standing Constraints

- **Settle each HYPOTHESIS first.** A refuted claim is dropped from its deliverable, not worked around.
- **The gate gets more precise, never more permissive.** Every relaxation ships with a control showing that a genuine loss still blocks.
- **One identity scheme for a test.** D1 changes the scheme in one place; the accepted set uses it.
- **One success-criteria parser.** D5 does not add a second parser; the retired-rule replay is the only migration aid.
- **Decisions go to scripts, not prose.** Prose changes route each decision to a script outcome a test can pin.
- **Documentation states the current behaviour.** No comment or doc describes a change or the old behaviour.
- **Tests state their purpose**, use the `PLAN_MARSHALL_HOME` fixture, and are shown red where a Done-when says so. A test that renames
  or inverts an existing control says why in its docstring; counts come from an enumeration, not a hand list.
- **No token or measurement work.** **No Sonar.**

## Claim Labels

- OBSERVED: after-identities are pooled across every after-file, before-counts are per file — `_review_support_integrity.py:411-430`,
  `:467-471`; a modified path is reported whenever its own file total drops, so a function moved to another file gives a row with
  `removed_tests=[]` — `:461-473`; the set-total row is attributed to the file with the most assertions before the change — `:492-504`.
- OBSERVED: a row with `removed_tests=[]` is never accepted — `review_support.py:249`; a declaration without a count accepts any count,
  drops included — `:258-274`; the count is optional — `_plan_parsing.py:821-823`.
- OBSERVED: the close recomputes from a fresh run over the working tree and keeps the last row per path — `_cmd_loop_back.py:441-458`,
  `:444`; it records an identity only for a finding whose title carries the weakened-test prefix — `:425-427`.
- OBSERVED: the re-arm applies to every record resolved `taken_into_account`, with no rule, source or phase filter — `_findings_core.py:1615`;
  the triage workflow records an operator Hold as `taken_into_account` — `plan-marshall/workflow/triage.md:327` and `:391`;
  `manage-findings/SKILL.md:262` says it "is the review's own supersession, not an operator decision".
- OBSERVED: the evidence root for `use_worktree: false` is the main checkout with no branch or dirty check — `_review_support_integrity.py:119-130`,
  `:324-327`; `merge_base` and `_show` run outside the `try` that catches a timeout — `:114,181,190,372-376`; a missing merge base falls
  back to the base tip — `:218-221,376`; `_show` returns `None` on any failure — `:188-191`; the after-image reads the working tree first — `:194-210`.
- OBSERVED: the class scope stack pops on any non-blank line at or below the class indent — `:270-282`; a skip marker goes to the next span at or after it — `:605-617`.
- OBSERVED: the retired-rule replay and the `parser_extended` classification — `_criteria_snapshot.py:855-879,1257-1282`; documents that contradict the code —
  `review-rubric.md:41,42`, `functional-review.md:301,303`.
- HYPOTHESIS: whether the triage Hold records live in the Q-Gate store where D3's re-arm applies (`triage.md:146-152,210-216`, the store a
  Hold resolves in) — confirm/refute at outline; it decides whether D3 needs a code scope or only the text.
- HYPOTHESIS: whether finalize can run a no-worktree plan with a mismatched or dirty main checkout (D4) — confirm/refute at outline.
- HYPOTHESIS: a no-identity row cannot be cleared by an operator close without `--accept` (L3-5; the deadlock rests on unread paths) —
  confirm/refute with a fixture at HEAD before D1 and D2 are cut.
- HYPOTHESIS: `_SUCCESS_BLOCK_END_RE` matches an indented bold-field line (L3-14; the regex was not read) and `SKIP_MARKERS` carries
  `it.skip(` as D1 assumes — confirm/refute at outline.
- HYPOTHESIS: the tests the analysis leaf named (`test_lb105_test_integrity_d1.py:153,187,417,537`, `test_lb105_reobservation_d3.py:175,208`)
  read as described — confirm/refute at outline.
- Verify-first clause (D1): reproduce the pooled-identity and moved-function shapes as fixtures at `ce29d4b1f` before editing; a shape that
  does not reproduce is reported and its Done-when narrowed in the PR.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_review_support_integrity.py` — the survival test, the row shape, the identity spans, the markers, the evidence root, the git helpers (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_support.py` — the acceptance test, the row kinds, the no-identity path (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_loop_back.py` — the close's recompute and the per-path keying (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py` — the count in a declaration (D2, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — the re-arm scope (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` — the dedup text (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md` — § 3e, Branch B (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md` — the removal rule, `parser_extended` (D2, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py` — the parser, the replay, the classification (D5)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_lb105_test_integrity_d1.py` — the loss, move and marker fixtures (D1, D4)
- OBSERVED: `test/plan-marshall/manage-status/test_lb105_accepted_removals_d2.py` — the acceptance and close fixtures (D2)
- OBSERVED: `test/plan-marshall/manage-findings/test_lb105_reobservation_d3.py` — the re-arm fixtures (D3)
- OBSERVED: `test/plan-marshall/manage-solution-outline/test_lb105_criteria_parser_d4.py` — the parser fixtures (D5)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_review_support_validate.py` — transitional wording (D5; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/manage-findings.py` — the `--reopen` help text (D3; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/code-review.md` — the partition restatement (D3; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-findings/test_qgate_resolution_survives_reemission.py` — the control for a Hold record (D3; verify-at-outline)

## Dependencies and Sequencing

- **Depends on:** the landing of PLAN-LB-105, which is on the base branch.
- **Overlaps with parked PLAN-LB-75** on `review_support.py` (D1) and `_criteria_snapshot.py` (D4): sequence the two; re-ground LB-75
  against this plan's line moves.
- **Overlap check at emit.** The gate decides the pairing. This plan declares explicit test files, not the `phase-6-finalize/` or
  `manage-findings/` directories, so it shares no file with PLAN-LB-107's directory entries by containment of a named file alone; the
  gate's read at emit decides, and an overlap prompt is asked if it reports two or more shared files with in-flight work.
- **Adjacent to** (left untouched): the finalize review gate's other verdict checks (PLAN-LB-107), the code-review recipe.
- **Owed outside this plan, operator-run:** a harness sync after merge.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-118-review-gate-grading-fix.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
