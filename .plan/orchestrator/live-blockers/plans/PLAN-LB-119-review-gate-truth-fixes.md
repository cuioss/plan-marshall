# PLAN-LB-119: The review gate stops failing open — merge-gate evidence is read from the head, a test loss is decided per identity, an acceptance covers exactly what was accepted

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-119-review-gate-truth-fixes.md` and is queued as one row file, `queue/PLAN-LB-119.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word ("can we create a combined plan for this and other known and upcoming fixes?", scope answered: the
> review-gate pair). It folds the unstaged fix plans for two shipped landings: PLAN-LB-118 (PR 1919, merge `75b5780d0`; report
> `landings/PLAN-LB-118.md`, decision 15) and PLAN-LB-106 (PR 1912, merge `5fd240a5e`; report `landings/PLAN-LB-106.md`, decision 12).
> Every finding id below (L1-n, L2-n, L3-n) is the id in the report named at its deliverable. Points the orchestrator re-read at their
> lines are OBSERVED; points a leaf read and the orchestrator did not re-read, and every claim about reach, are HYPOTHESIS and are
> settled first. Fixes from plans still running (PLAN-LB-107, 108, 110) are NOT in this spec: they are specced when those plans
> ship and are analysed, and join this plan only if it has not been emitted by then.
>
> Ruling check. Both halves are the "review gate can be trusted to mean what it says" done-condition of the epic vision. D1 is a
> live fail-open in the merge gate (graded blocking). D2 to D4 are gate passes or dead-ends found on the finalize test-integrity gate.
> D5 to D7 are minor to medium and separable. No token or measurement work. No Sonar.

## Objective

Two review gates were rebuilt in the last round and each shipped with defects that let something through that the gate says it
holds. The merge gate credits a CodeRabbit inline comment as a review of the merge candidate because GitHub reports the comment's
`commit` at the newest head while the line stays in the diff, so a refused head can read as reviewed. The finalize test-integrity
gate treats a bare test name in a new file as proof that a modified file's assertions moved, accepts a later skip of the same kind
as the one an operator accepted, drops a second filter acceptance on a path, and records a close at a head nobody re-validated.

After this plan the merge gate reads where the provider PLACES a comment from the fields that do not follow the newest head, a loss
is decided per identity with a move proven by content, an acceptance names what it covers and covers nothing else, a close at an
unvalidated head is refused or re-validated, and the evidence root, the git calls and the parser state what they could not read.

## Deliverables

1. **The merge gate reads where a comment was placed from a field that does not follow the newest head.** *(PLAN-LB-106 report: L3-1,
   L3-2, L3-6; blocking)*
   - `_inline_comment_placement` reads the comment's own `commit` first and the review's commit only as a fallback
     (`github_ops.py:705-709`). The placement uses the field that names the commit the comment was posted at (`originalCommit` on the
     comment, or `pullRequestReview.commit`) and the comment's own `commit` only when neither is present; the field order is decided
     from the live record named under Claim Labels and recorded.
   - The inline rule credits a non-reply inline comment when its commit equals the merge candidate (`github_pr.py:2111-2118`). With
     the placement corrected, an old comment is placed at the head it was posted at and is stale.
   - L3-2, a lead: a summary comment that carries the coverage marker AND a quota-refusal block is skipped whole as a refusal
     (`github_pr.py:2093`), so a finished review's marker is never read. Settle first whether CodeRabbit keeps the limit block in the
     summary after it finishes a review; if it does, a comment that carries a readable coverage marker is read for the marker before the
     refusal skip applies; if it does not, the lead is refuted and dropped.
   - L3-6: the inline rule is bot-agnostic and also governs `cuioss-review-bot`, which declares inline evidence. The outline records
     whether the rule is meant to govern it; the bot's removal is parked PLAN-LB-46's D7 and is not done here.

   *Done when:* a fixture whose inline comment has `commit` at the newest head, `originalCommit` at an older head and a quota refusal
   for the newest head does not credit the bot (red at the merge `5fd240a5e`); the same comment as a reply is still never evidence
   (control); a fixture built from the live shape of PR 1912's comment is not credited; the marker-plus-limit-block fixture is
   decided by the settled lead (credited, or the lead is refuted in the PR); existing controls stay green: a comment placed at the
   candidate by the review's commit is credited, and a refusal with no placement still does not credit.

2. **A loss is decided per identity, and a move is proven by content.** *(PLAN-LB-118 report: L3-1, L1-3, L3-3, L1-7; major)*
   - A deleted test identity that is absent from a modified file's after-set is a move only when its assertion content survives
     elsewhere. A bare name in another file does not prove a move (`_review_support_integrity.py:648-666`); the comparison reuses the
     content check the identity-less path already applies (`:630`) or a stated equivalent, decided at outline and recorded in the
     module docstring and § 3e of `functional-review.md` once.
   - The set-total row is attributed to the file whose loss no identity explains, not the file with the largest raw drop
     (`:690-697`, L1-3).
   - A path-level acceptance key is typed by row kind: a mixed-residual entry accepts a residual and nothing else, a file-total entry a
     file total, a set-total entry a set total (`review_support.py:307-312,321-327`, L3-3).

   *Done when:* a fixture deleting `test_parse` (two assertions) from a modified file while a new file adds an unrelated `test_parse`
   with two `assert True` yields a row (red at `75b5780d0`); a function moved with its assertions yields no row (control); a fixture
   with an unexplained loss in file Q and a larger explained drop in file P attributes the set-total row to Q (red); a mixed-residual
   entry does not accept a file-total row of the same count (red). The pre-existing controls (a wholly deleted file, a named-test
   removal, a move to a new test, a skip marker) each still yield a row.

3. **An acceptance covers exactly what was accepted, and a second acceptance on a path is recorded.** *(PLAN-LB-118 report: L3-2, L3-4;
   major; delivered with D2, which shares the row shape and the acceptance key)*
   - A filter acceptance names what it covers, as the removal key names identity plus count: the marker kind plus the number of
     marked tests, or the identity of each marked test, decided at outline. A later skip of a further test in the same file is a new
     row (`review_support.py:313-320`).
   - The accepted-set key includes what the entry names (`_criteria_snapshot.py:361-366,421-437`), so a second close on a path whose
     marker set differs is appended and the writer reports success only when it appended or the entry was already present.
   - The close and `review_support` read one key.

   *Done when:* accepting `it.skip('a')` and then adding `it.skip('b')` to the same file raises a row (red at `75b5780d0`); a second
   close for `{path, test_filtered, [describe.skip, it.skip]}` after an earlier close for `[it.skip]` is recorded and the row is not
   raised at the next head (red); re-seeding the same entry neither duplicates nor drops it (control).

4. **A close at a head that was not validated is refused or re-validated.** *(PLAN-LB-118 report: L1-1 lead, C9)*
   - Settle first, at the re-fire and pre-merge barrier, whether a step recorded done at a closing head B is re-graded at B. If it is,
     the lead is refuted and the PR says so; the C9 documentation below still ships.
   - If it is not: `loop-back close` compares the closing head to the validated head (`_cmd_loop_back.py:648-665,691-694`) and
     refuses with a named state, or re-runs the integrity validation at the closing head and records only what that run accepted. The
     spec of PLAN-LB-118 said "refused or re-validated"; this deliverable chooses and pins one.
   - A pre-marker `taken_into_account` record from a loop-back round is `kept` on a re-file and fails closed; the escape
     (`qgate resolve --resolution pending`) is stated in `functional-review.md` Branch B, not only in `manage-findings/SKILL.md`.

   *Done when:* (if not re-graded) a close at a head that differs from the validated one is refused or re-graded and a removal made at
   the later head is not recorded unseen (red at `75b5780d0`); (always) a doc test pins the escape sentence in Branch B.

5. **The evidence root and the git calls fail closed.** *(separable; PLAN-LB-118 report: L1-2, L3-6, L3-7, L1-6)*
   - A `use_worktree: false` plan is graded only when the main checkout is carrying the plan's work: its HEAD is the plan's recorded
     branch (when the plan record carries one) or the tree is otherwise proven to be the plan's, and it is clean
     (`_review_support_integrity.py:443-466`). Otherwise `evidence_root_unresolved`.
   - `_is_ancestor` separates exit 1 (not an ancestor) from any other exit (a failure, `test_integrity_not_run`)
     (`:402-404,455-458`).
   - `_ABSENT_PATTERNS` reads a missing path as absent and a missing revision as a failure (`:241-247`); the broad `path '` entry is
     removed or anchored.
   - Changed paths are read NUL-delimited, so a path with `"`, `\`, TAB or LF is read, not C-quoted (`:157,191-203,262-263`).

   *Done when:* a no-worktree plan on a clean checkout of another plan's branch does not return success with zero rows (red); a
   `--is-ancestor` that exits 128 is `test_integrity_not_run` (red); a deleted test path containing `"` is read and its loss
   reported (red); the existing missing-merge-base, timeout and non-ASCII fixtures stay green.

6. **The parser reports what it dropped, and the documents state the current behaviour.** *(separable; PLAN-LB-118 report: L3-5, L1-4,
   L1-5, L3-9, C14 a and b)*
   - A fenced block under a criterion is either kept in the criterion text as before or reported under `unparsed`; it is never
     silently dropped (`_criteria_snapshot.py:884-891`). Fence recognition follows CommonMark (indent at most three, a backtick fence
     whose info string has no backtick), and an unterminated fence is a named state a gate reads, not only a field of the freeze
     payload. Settle first the base behaviour and the `criteria_drift` consumer (HYPOTHESIS below).
   - Documents and comments state the current behaviour: `_review_support_integrity.py:316-317` (a row with no identity is now
     acceptable by path), the module docstring's "Both key the accepted set" antecedent and the count-less rule
     (`:37`), `functional-review.md:298` and § 3e (a HEAD behind base is also refused; a filter row's acceptance), `review-rubric.md:41`,
     the `_reopen_qgate_record` docstring (`_findings_core.py:1476-1479`), `manage-findings/standards/jsonl-format.md:254,297-304`
     (the observation-reopen row; `resolution_source`).
   - The doc test pins the count-less rule beside the four-cases sentence.

   *Done when:* a fixture with a fenced example under a criterion edited between freezes is reported by a named state or its text is
   in the criterion (red at `75b5780d0`); an unterminated fence is read by the gate; a read of each cited line shows the wording
   corrected.

7. **The review-bot evidence minors.** *(separable; PLAN-LB-106 report: L3-4, L3-3, L2-3, L1-1, L1-2, L2-1, L2-2, L2-6, L3-8)*
   - A review body over 64 KiB keeps its conclusion: the quarantine cut is not head-only before ingest keeps its tail
     (`_findings_core.py:188-189`), and `original_length` reports the true length.
   - The Sourcery footer strip handles a footer spread over several lines, and a clean Sourcery body is not filed as a finding that
     needs triage (`github_pr.py` footer strip, `sourcery.md:22-25`).
   - A review body that quotes a coverage marker does not override the provider's `commit_id`, and a nested JSON payload is read
     (`_github_pr.py` coverage pattern).
   - The marker name and its field names come from registry data, as the standing constraint of PLAN-LB-106 said, or the departure is
     stated at its owner.
   - `runbook-lane/SKILL.md:699-704` and the parser agree on which head a credited marker names; the runbook-lane guard reads its
     field list from `_github_pr`.
   - The weak tests are tightened: the D4 ingestion test of PLAN-LB-106 injects records after the fetch (the fetch layer is not
     covered), `count_skipped_noise >= 1` is loose, one currency test asserts the classifier and not `pre_merge_gate merge`, and the
     participation-site guard's population omits the placement site.

   *Done when:* each of these fails at `5fd240a5e` where it is a behaviour (an over-limit body keeps its tail; a multi-line footer
   leaves no markup; a quoted marker does not override the provider commit), and each test change is shown to fail against a stub
   of the behaviour it pins.

Split guard: seven deliverables on two review gates. This exceeds the six-deliverable guard on the operator's word (the combined
plan was asked for); the rationale is recorded in the epic decision log. D2 and D3 share the row shape and the acceptance key and are
delivered together; D4 is independent but edits the same close module; D5, D6 and D7 are the first to split off, in that order. A
split runs in sequence, since D2 to D6 edit one module family. D1 is the first stage: it is the live fail-open and shares no file
with D2 to D6.

## Standing Constraints

- **Settle each HYPOTHESIS first.** A refuted claim is dropped from its deliverable, not worked around, and the PR says so.
- **The gate gets more precise, never more permissive.** Every relaxation ships with a control showing that a genuine loss or an
  unreviewed head still blocks.
- **Required reviewers keep their text.** The standing review authorization, the required-reviewer rule and the quota policy are not
  weakened; D1 only tightens what counts as evidence.
- **Fail closed.** An unreadable review surface, an unparsable body, an errored git call or an undecidable read is a stop, never a
  pass.
- **One identity scheme for a test, one acceptance key.** D2 and D3 change them in one place each; the close and the check use them.
- **One success-criteria parser.** D6 does not add a second parser.
- **Decisions go to scripts, not prose.** A prose change routes each decision to a script outcome a test can pin.
- **Documentation states the current behaviour.** No comment or doc describes a change or the old behaviour.
- **Tests state their purpose**, use the `PLAN_MARSHALL_HOME` fixture, and are shown red where a Done-when says so. A test that renames
  or inverts an existing control says why in its docstring; counts come from an enumeration, not a hand list.
- **No token or measurement work.** **No Sonar.**

## Claim Labels

- OBSERVED: the placement reads the comment's own `commit` first and the review's commit only when it is absent —
  `workflow-integration-github/scripts/github_ops.py:705-709`; the inline rule credits a non-reply inline comment when its commit
  equals the candidate — `github_pr.py:2111-2118`; a refusal notice is skipped whole before the marker is read — `github_pr.py:2093`.
- OBSERVED: live record on PR 1912: CodeRabbit comment `PRRC_kwDOQ3xasM8AAAABCyVDVA`, created 2026-11-05 14:52:35, opening its thread,
  resolved, reports `commit_id b09d230fc…`, the final head, while CodeRabbit's own summary says "Latest commit, not reviewed:
  b09d230" (PLAN-LB-106 report, L3-1).
- OBSERVED: the quarantine cuts head-only at the byte cap and appends a marker — `manage-findings/scripts/_findings_core.py:188-189`.
- OBSERVED: a survival comparison per identity reads a bare name in another file as carried — `_review_support_integrity.py:648-666`
  (`carried = 0`, `surviving = 2`, `residual = 0` for the fixture of D2); the set-total row goes to `max(positive)` of the raw
  per-path drop — `:690-697`; one path-level key serves three row kinds — `review_support.py:307-312,321-327`.
- OBSERVED: a filter row is accepted when its marker set is a subset of an accepted entry's — `review_support.py:313-320`; the
  accepted-set key omits `markers` — `_criteria_snapshot.py:361-366,421-437`.
- OBSERVED: the close marks the step done at `head`, then records the rows of the previous record's `head_at_completion` —
  `manage-status/scripts/_cmd_loop_back.py:648-665,676,691-694` (comment at `:688-690` states it).
- OBSERVED: the evidence guard compares HEAD to the base ref only and checks the tree is clean —
  `_review_support_integrity.py:443-466`; `_is_ancestor` reads any non-zero exit as "not an ancestor" — `:402-404`; the absent
  patterns include `invalid object name`, `unknown revision` and `path '` — `:241-247`.
- OBSERVED: a fence line and everything until its close is skipped without a record, an unterminated fence is added to `unparsed`
  only — `manage-solution-outline/scripts/_criteria_snapshot.py:884-891,912-915`.
- OBSERVED: stale wording at `_review_support_integrity.py:316-317` and the "Both key the accepted set" sentence at `:37`.
- HYPOTHESIS: `originalCommit` (or `pullRequestReview.commit`) does not follow the newest head for a comment on a line that stays in
  the diff — confirm/refute against the live record above and `github_ops.py` § the GraphQL fragment (verify-at-outline). It decides
  the field order of D1.
- HYPOTHESIS: CodeRabbit keeps the "Review limit reached" block in the summary comment after a finished review — confirm/refute
  against `automatic-review/standards/coderabbit.md` and a live summary (verify-at-outline). It decides whether D1's lead stands.
- HYPOTHESIS: a step recorded done at a closing head is re-graded at that head by the re-fire or pre-merge barrier — confirm/refute at
  `phase-6-finalize` § the re-fire logic and `pre_merge_gate.py` (verify-at-outline). It decides whether D4 is code or text.
- HYPOTHESIS: the base code (`c394a95fb`) did not skip fenced lines under a criterion, and no gate consumes a fence-drift state —
  confirm/refute at `_criteria_snapshot.py` § `criteria_drift` (verify-at-outline).
- HYPOTHESIS: `references.json` or the plan record carries the plan's branch name, so D5 can compare HEAD to it — confirm/refute at
  `manage-references` and `_review_support_integrity.py` § `_evidence_root` (verify-at-outline). If it does not, D5 states the
  narrower rule in the docstring and the first bullet is dropped.
- HYPOTHESIS: `git diff --name-only -z` is available on every supported git — confirm/refute at the build's minimum git version
  (verify-at-outline).
- HYPOTHESIS: the Sourcery and nested-marker minors of D7 reproduce on real bodies — confirm/refute with a fixture from a live
  Sourcery body and a quoted-marker review body (verify-at-outline). A shape that cannot be reproduced is reported and its bullet
  dropped.
- Verify-first clause (D1): reproduce the old-comment placement as a fixture at `5fd240a5e` before editing. A shape that does not
  reproduce is reported and its Done-when narrowed in the PR.
- Verify-first clause (D2): reproduce the bare-name absorption as a fixture at `75b5780d0` before editing.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` — the placement (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — the inline rule, the refusal skip, the footer strip (D1, D7)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — the coverage marker parser (D1, D7)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_review_support_integrity.py` — survival, set-total row, evidence root, git helpers, docstring (D2, D5, D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_support.py` — the acceptance test and keys (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_loop_back.py` — the close (D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py` — the accepted-set key, the fence handling (D3, D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — the quarantine cut, the reopen docstring (D6, D7)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md` — § 3e, Branch B (D2, D4, D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md` — the removal and acceptance rule (D2, D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md` — the dedup table (D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — the marker-head text at L699-704 (D7)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_ops_pr_comments.py` — placement fixtures (D1)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr_currency.py` — the credit and refusal fixtures (D1, D7)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_comments_stage_fetch.py` — the fetch-layer fixtures (D7)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_lb118_test_integrity_d1.py` — the loss fixtures (D2)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_lb118_integrity_evidence_root_d4.py` — the evidence-root fixtures (D5)
- OBSERVED: `test/plan-marshall/manage-status/test_lb118_accepted_removals_d2.py` — the acceptance and close fixtures (D2, D3, D4, D6)
- OBSERVED: `test/plan-marshall/manage-solution-outline/test_lb118_criteria_parser_d5.py` — the parser fixtures (D6)
- OBSERVED: `test/plan-marshall/manage-findings/test_findings_ingest.py` — the cut and elision fixtures (D7)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` — the marker-text guard (D7)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — the classifier the credit outranks a refusal at (D1; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/untrusted-ingestion/scripts/validate_struct.py` — the elision (D7; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md` — the footer markers (D7; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` — the marker as registry data (D7; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/automatic-review/test_participation_site_population_guards.py` — the population guard (D7; verify-at-outline)

## Dependencies and Sequencing

- **Depends on:** the merges of PLAN-LB-118 (`75b5780d0`) and PLAN-LB-106 (`5fd240a5e`), both on the base branch.
- **Overlaps with PLAN-LB-108 (running) and PLAN-LB-116 (staged)** on `runbook-lane/SKILL.md` and `test_runbook_lane.py`, through D7's
  marker-text bullet only; run D7 after both, or drop that bullet. The gate decides the pairing at emit.
- **Overlaps with PLAN-LB-107 and PLAN-LB-110 (running)** on the `phase-6-finalize/` test directory only if the gate reads a directory
  entry; this spec names explicit files. The gate's read at emit decides; an overlap prompt is asked at two or more shared files.
- **Overlaps with parked PLAN-LB-75** on `review_support.py` and `_criteria_snapshot.py`, and with parked PLAN-LB-46 on the bot
  participation rules (D1, L3-6): re-ground both against this plan's line moves before either is un-parked.
- **Adjacent to** (left untouched): the finalize review gate's other verdict checks (PLAN-LB-107), the code-review recipe, the
  removal of `cuioss-review-bot` (PLAN-LB-46 D7), and the Q-Gate `resolution_source` semantics shipped by PLAN-LB-118.
- **Owed outside this plan, operator-run:** a harness sync after merge. No verb or flag is added unless the outline decides D4 needs
  one; then an executor regeneration is owed and the landing says so.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-119-review-gate-truth-fixes.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
