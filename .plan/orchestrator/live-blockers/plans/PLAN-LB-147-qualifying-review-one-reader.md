# PLAN-LB-147: A qualifying review has one reader — the post chokepoint, the producer and the lane agree, and the prose says what the code does

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-147-qualifying-review-one-reader.md` and is queued as one row file, `queue/PLAN-LB-147.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word of 2026-11-11 ("do propose and emit") as the fix plan for the PLAN-LB-142 landing analysis
> (`landings/PLAN-LB-142.md`: one layer-3 major, L3-1, and a cluster of minors on the same three files). One plan for one surface,
> per the operator's rule of the same day. Grounded against `main` at `280e6c404` by a read-only three-layer leaf, with the orchestrator
> re-reading the chokepoint, the producer's finished-review test, the done arm of `resolve_recovery_action` and the done arm and its
> comment in `classify_bot`. Every Done-when below fails at `280e6c404` unless it is a stated hold. No Sonar. No token or measurement work.

## Objective

PLAN-LB-142 made one handled CodeRabbit review the review, and the rule rests on one question — is a finished review on record — that
three places answer with three different predicates. The producer (`github_pr`) admits a formal review to `finished_review_bots[]` only
with a commit or a marker that names one; the post chokepoint (`github_re_review`) admits any non-refusal formal review; the lane's
`review-gate --required-reviewer` has a third reading. For a formal review with an empty commit the chokepoint says "on record" and refuses
every re-review post while the producer leaves the bot stale and the trigger list names it, so the pull request can sit with no way to
re-request and no review that counts. This plan gives the question one reader, pins that the sites agree, and makes the prose and comments
say what the code does.

## Deliverables

1. **The post chokepoint and the lane use the producer's finished-review predicate.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - `_qualifying_review_on_record` (`github_re_review.py`) and the lane's `--required-reviewer` check (`runbook_lane.py`) decide "a finished
     review is on record" through the one predicate the producer applies when it builds `finished_review_bots[]` (`github_pr.py`): a
     formal review counts only with a non-empty commit or a finished marker that names one, and a refusal-shaped body counts only when it
     also carries a readable finished marker. The private copy `_is_refusal_body` in `github_re_review.py` is retired, and the lane stops
     importing it from another skill's script.
   - The producer's refusal test (`_is_refusal_notice`, in `_github_pr.py`) is reachable from `github_re_review.py` without a cycle; the
     module already imports from `_github_pr`, so the docstring's stated reason for the duplicate (the producer lives in a module that
     imports this one) is checked and, if false, removed with the copy.
   - Decide at outline, and record in the PR: whether the commit a marker or a review names must be one of this pull request's heads. The
     PLAN-LB-142 lane answered the point with a reason (a new provider read) and this spec's default is to leave it so and disclose it in the
     document; the leaf graded it minor.

   *Done when:* each of these fails at `280e6c404`: a CodeRabbit `review_body` with an empty `commit_id` and no marker is reported as no
   finished review by the chokepoint, as the producer already does; a `review_body` whose commit is present but whose body only the
   enumerative refusal arm reads as a refusal gets the same verdict from the producer, the chokepoint and the lane's `review-gate`. These
   hold at `280e6c404`: a `review_body` with a commit is on record; a marker-bearing issue comment whose marker names a commit is on
   record; a body that is a refusal and carries a readable finished marker is on record at every site.

2. **The three sites are pinned to agree, and the one test that pinned the disagreement is moved.**
   - Skills: pm-dev-python:python-core, pm-dev-python:pytest-testing
   - Persona: module-tester
   - One shape-table test drives the producer, the chokepoint and the lane check over the same artifacts — a formal review with and without
     a commit, a marker with and without a commit, a refusal with and without a marker, an in-progress summary, a walkthrough — and asserts
     one verdict per artifact. A second invariant is pinned over `trigger-bot` and `request_fresh_review`: for one bot and one history they
     never both hold, so a bot the chokepoint refuses to trigger as "done" is never the bot `trigger-bot` lists.
   - The test that pins the empty-commit case as a qualifying review
     (`test_review_complete_after_handling_re_review.py`, about L141) is moved to the agreed reading, never deleted without a replacement.
   - The scoped-join control in `test_trigger_b_stale_set_from_participation.py` (about L388) gets its CodeRabbit subject back beside the
     Sourcery one, because the done filter needs `finished_review_bots` and that helper passes none, so the switch was not needed.

   *Done when:* the shape-table test passes on the changed code and fails on a planted second predicate at any one of the three sites; the
   invariant test fails at `280e6c404` for the empty-commit review. These hold at `280e6c404`: every test of the done rule that passes
   today still passes, apart from the moved empty-commit case.

3. **The prose and the comments say what the code does.**
   - Skills: pm-documents:ref-documentation
   - Persona: documenter
   - The `resolve_recovery_action` docstring (item 8, about L926-933) and the `workflow-integration-github/SKILL.md` prose and table row
     (about L1333) state that the done arm admits an `undecidable` review state and runs ahead of every cause, window and budget arm; the
     code does both (`github_re_review.py` L997-1017).
   - The comment at `review_completeness.py` L1027-1029, which says a refusal or decline on the candidate still outranks the done branch,
     is rewritten: the done arm at L982-988 returns before the refusal arms, and the comment's own next lines say so.
   - The comment at `github_re_review.py` about L1075 ("a flagged bot never reaches this line") is corrected: a flagged bot with no review
     on record reaches `close_and_reopen`.
   - The comparative wording the leaf found ("the behaviour it had before either flag existed", "keeps today's behaviour",
     "triggered exactly as before", "posts exactly as before") is replaced by a statement of the current behaviour, in
     `bot_registry.py`, `phase-6-finalize/standards/branch-cleanup-rereview.md`, the `list_bots_for_trigger` docstring and
     `github_re_review.py`.
   - The documentation test pins each corrected statement in the section that states it, with a planted-old-sentence control.

   *Done when:* the documentation test passes on the changed documents and fails on a planted copy of each old sentence; it fails at
   `280e6c404` because the documents and comments state the old reading.

4. **The lane's re-split of a flattened review body is fence-aware.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - The lane re-splits a flattened body by inserting a newline before every `<!--` (`runbook_lane.py`, about L2692), after flattening has
     erased the fence lines, so a marker quoted inside a fenced block reads as the bot's claim and satisfies the check. The re-split reads
     comment boundaries from the unflattened body, or skips a marker inside a fence, so a quoted marker counts for nothing.

   *Done when:* each of these fails at `280e6c404`: a review body that quotes a finished marker inside a fenced block is not a qualifying
   review at the lane's check. These hold at `280e6c404`: a body carrying the same marker outside a fence is a qualifying review; a body
   with several comments flattened onto one line still splits at each comment boundary.

Split guard: four deliverables, one theme (one question, one answer). D1 is the code, D2 the pins, D3 the prose, D4 the lane's parse; D3 and
D4 share no function with D1 and can ship separately if one is blocked, which the PR records.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- One reader per concept: the finished-review predicate lives in one module and the other sites call it; no site keeps a private copy.
- Fail closed: an unreadable fetch, a capped history and an undecidable review state are never read as "done"; the chokepoint's fail-open
  is for the POST decision only, as PLAN-LB-142 shipped it, and this plan does not widen it.
- The done rule's behaviour for a review that IS finished is unchanged: the arm order in `classify_bot` and `resolve_recovery_action`, the
  `review_on_record_done` refusal and the pending-findings blocks stay as shipped.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture and are shown red where the Done-when says so.
- The PR states whether an executor regeneration is owed (this plan adds no verb or flag if the predicate is shared by import).
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: the chokepoint returns true for any `review_body` that is not a refusal OR carries a marker that names a commit, with no `commit_id` test — read at `workflow-integration-github/scripts/github_re_review.py` § `_qualifying_review_on_record`, L1934-1942
- OBSERVED: the producer admits a formal review to `finished_review_bots` only with a non-empty `commit_id` or a marker that names a commit, and skips a refusal-shaped body unless it carries a finished marker — read at `workflow-integration-github/scripts/github_pr.py` L2205-2222
- OBSERVED: the chokepoint's refusal test `_is_refusal_body` adds the enumerative arm (`_is_unrecognised_refusal`) to the structural and registry arms, and its docstring gives the producer's module importing this one as the reason for not importing `_is_refusal_notice` — read at `github_re_review.py` L1876-1891
- OBSERVED: the `resolve_recovery_action` done arm admits `REVIEW_ON_RECORD_UNDECIDABLE` beside credited and stale, and runs ahead of the condition, cause, window and budget arms — read at `github_re_review.py` L997-1017
- OBSERVED: the done arm in `classify_bot` returns before the refusal arms, and the comment at L1027-1029 states the opposite while L1031-1033 states the truth — read at `automatic-review/scripts/review_completeness.py` L982-1034
- HYPOTHESIS: `_is_refusal_notice` lives in `_github_pr.py` and `github_re_review.py` already imports from that module, so the stated reason for the duplicate is false — confirm/refute at `workflow-integration-github/scripts/_github_pr.py` § `_is_refusal_notice` and the import block of `github_re_review.py` (leaf read, L189 and L270-292; verify-at-outline)
- HYPOTHESIS: the lane's `--required-reviewer` check is a third reading (`_is_refusal_body` plus a names-commit exemption), requires a bot-authored artifact whatever the flag says, and imports `_is_refusal_body` from another skill's script — confirm/refute at `runbook-lane/scripts/runbook_lane.py` L2669-2718 and L2832-2846 (leaf read; not re-read by the orchestrator)
- HYPOTHESIS: a null-commit review (the GraphQL `commit` field is nullable) is the trigger of the loop: the producer leaves the bot out of `finished_review_bots`, `classify_bot` reads it stale, `trigger-bot` lists it, and every post is refused as `review_on_record_done`; the step-done guard then loops back and the pre-merge gate refuses until an operator authorizes — confirm/refute at `workflow-integration-github/scripts/github_ops.py` L771-773, `review_completeness.py` § `list_bots_for_trigger`, `phase-6-finalize/scripts/pre_merge_gate.py` L956-1023 (leaf read; the loop-back and the refusal were not re-read)
- HYPOTHESIS: the test at `test_review_complete_after_handling_re_review.py` about L141 pins the empty-commit review as a qualifying one, and the test at about L407 pins the undecidable arm — confirm/refute by reading both (leaf read; not re-read)
- HYPOTHESIS: the lane's flattened-body re-split inserts a newline before every `<!--` after the fence lines were erased by flattening — confirm/refute at `runbook-lane/scripts/runbook_lane.py` L2669-2718 and `_github_pr.py` L521-545 (leaf read; not re-read)
- HYPOTHESIS: the prose and docstring half of the undecidable finding sit at `workflow-integration-github/SKILL.md` about L1333 and its table row and at `github_re_review.py` L926-933 — confirm/refute by reading both (leaf read; not re-read)
- HYPOTHESIS: the comment "never reaches this line" is false for a flagged bot with no finished review, which the test at about L467-478 asserts — confirm/refute at `github_re_review.py` about L1075 (leaf read; not re-read)
- HYPOTHESIS: comparative wording remains at `bot_registry.py` (about L1004), `phase-6-finalize/standards/branch-cleanup-rereview.md` L15, the `list_bots_for_trigger` docstring and `github_re_review.py` L1232-1233 — confirm/refute by reading each (leaf read; not re-read)
- HYPOTHESIS: the scoped-join control in `test_trigger_b_stale_set_from_participation.py` about L388 switched its subject from coderabbit to sourcery without need — confirm/refute at that file (leaf read; not re-read)
- Verify-first clause: before scoping D1, reproduce the loop by driving the chokepoint and the producer with one empty-commit `review_body` fixture and state what each returns; a refuted loop narrows D1 to the one reader and drops the claim of a stranded pull request from the PR.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` — `_qualifying_review_on_record`, `_is_refusal_body`, `resolve_recovery_action` docstring, the comment at about L1075 (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — the `finished_review_bots` build at L2205-2222, only if the predicate moves (D1; prefer no change)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — `_is_refusal_notice`, the shared predicate's home (D1; verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — the `--required-reviewer` check and the flattened-body re-split (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — the comment at L1027-1034 and the `list_bots_for_trigger` docstring (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` — the comparative wording at about L1004 (D3; verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md` — the done-arm prose and table row (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup-rereview.md` — the comparative wording at L15 (D3)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_review_complete_after_handling_re_review.py` — the moved empty-commit case (D2)
- OBSERVED: `test/plan-marshall/automatic-review/test_trigger_b_stale_set_from_participation.py` — the restored CodeRabbit control (D2)
- OBSERVED: `test/plan-marshall/automatic-review/test_review_complete_after_handling_docs.py` — the documentation pins (D3)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane_review_gate.py` — the lane check's verdicts and the fence case (D1, D4)
- HYPOTHESIS: a new shape-table test module in the directory of the re-review test above; its file name is chosen at outline (D2)

## Dependencies and Sequencing

- Depends on: PLAN-LB-142 (shipped, `280e6c404`).
- Overlaps with: PLAN-LB-144 on the review-completeness and merge-gate surface (`review_completeness.py` and the participation contract documents); the cross-check names the exact files. This plan edits comments and the finished-review predicate and PLAN-LB-144 edits `_scope_findings`, `_read_pr_comment_findings` and `_participation_refusal`, which share no function; name functions and not lines at outline. Sequence after PLAN-LB-144 unless the gate scores the overlap at one file.
- Adjacent to: the layer-3 defect's spec-premise Watch (the spec asserted that close-and-reopen resets done; the leaf reads the mechanism as keeping the number) and the phase-6 thread question (L3-7, not shown by reading) — both stay Watches and are not in this plan; and the foreign-commit marker point (a marker naming a commit outside the pull request satisfies the lane check), whose default here is a document statement and not a provider read.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-147-qualifying-review-one-reader.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
