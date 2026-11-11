# PLAN-LB-142: A handled CodeRabbit review is the review — no trigger, wait or currency demand follows it

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-142-coderabbit-review-done-after-handling.md` and is queued as one row file, `queue/PLAN-LB-142.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word of 2026-11-10: "In order to economize with the number of reviews, we should ensure that after each
> successful review including ALL handling of the result there should be no further review. The review is to be considered done and
> the plan / lane should merge." Grounded against `main` at `15aae32c6` (PLAN-LB-132 `3ed0888ea` is in the base). Every Done-when below
> fails at `15aae32c6` unless it is a stated hold. The grounding read of PLAN-LB-132's own run is the evidence for the cost: one
> pull request took three CodeRabbit reviews, two quota refusals and an "already reviewed the last commit" reply, all of it after the
> first review. No Sonar. No token or measurement work.

## Objective

CodeRabbit's review allowance is spent faster than a pull request needs it, because every push after a review makes the bot's
review "stale" and the machinery asks again: the automatic-review loop-back trigger, the branch-cleanup rebase trigger, the
elapsed-window re-trigger, the lane's "after every push, re-trigger", and the merge gates that refuse a review that predates the head.
This plan makes one qualifying CodeRabbit review on a pull request, once every finding of it is handled, the review: nothing posts a
further CodeRabbit trigger on that pull request, nothing waits for another, no gate asks for a review of the later head, and the
plan or lane proceeds to merge. A pull request with no qualifying review is untouched: the first trigger and the quota policy stand.

## Settled Design (the operator's rule as given, plus the defaults this spec chose — each is a decision the plan implements, not a question)

1. **Scope.** The rule is per pull request and per bot, and applies to a bot that carries a new per-bot registry flag (name decided at
   outline, declared in the bot's registry data block). CodeRabbit sets it. Sourcery and every other bot keep today's behaviour;
   a bot without the flag is unchanged. The flag is not `quota_limited`, because Sourcery declares that too.
2. **"The one review"** is the review the lane already calls qualifying (`runbook-lane/SKILL.md:820-828`): a formal review on one of
   this pull request's heads listed with its commit id, or the marker-bearing summary comment whose `kind=reviewed` names one of this
   pull request's heads, read through `_github_pr.review_coverage_verdict`. A refusal, a rate-limit notice, an acknowledgment
   (`Review triggered`, `Review finished`), a skip notice, an "already reviewed the last commit" reply, an in-progress summary and a
   marker-less walkthrough are not a review. The head the review covered need not be the current head.
3. **"All handling complete"** is the existing definition: every finding of the review is fixed in a pushed commit or answered with a
   stated reason and its thread resolved (`review-gate` `merge_allowed: true` in the lane; no pending PR-scoped finding of the bot in
   the finalize path), and every reply the producer holds until the fix commit is on the head with CI green has been sent.
4. **Done.** Once the bot's qualifying review is on record on this pull request, no path posts a CodeRabbit trigger for it — whether or
   not handling is complete yet (an unhandled review is handled, never re-requested). The same holds across the handling's own fix
   commits, a merge of the base branch and a branch-cleanup rebase. The rule removes the request, the wait and the currency
   demand; it does not remove handling.
5. **Late comments are still handled.** A CodeRabbit comment that arrives after done (an in-place edit of its summary comment, an
   unrequested review) is still ingested; an unresolved thread, an undispositioned body finding or a resolved finding that an edit reset
   to pending still blocks the merge through `review-gate` and the pending-findings predicates. Done stops requests, not handling.
6. **No review on record is untouched.** First trigger when none exists, the 90-minute quota wait, the escalated command, close-and-reopen
   and "never merge without the review" stand as written, because the economy is bought only after a review exists.
7. **Fix commits merge unreviewed.** This is the operator's intent. The merge gates still require build, CI, the review-gate and the
   other reviewers' conditions on the current head; only the CodeRabbit currency demand is dropped.
8. **The lane's standing authorization** (`runbook-lane/SKILL.md:817-833`, which needs a post-push re-trigger and `quota_limited`) stays
   for a quota-limited reviewer without the new flag, and is superseded for a flagged bot.

## Deliverables

1. **A flagged bot with a qualifying, handled review is complete at any later head.**
   - The per-bot flag is registry data parsed by `bot_registry.py` and declared in CodeRabbit's registry data block
     (`automatic-review/standards/coderabbit.md`, the block near L41-60).
   - `review_completeness.classify_bot` (`automatic-review/scripts/review_completeness.py`, the `stale_participants` arm at L963-964) reads a
     flagged bot that the producer reports stale, and that holds a qualifying review on this pull request, as `participated` (or
     `participated_but_empty`), not `participated_stale`; `check_completeness` therefore reports participation complete when handling is.
     Pending PR-scoped findings of the bot still block (`triage_ran` arm, L1517-1533). An unreadable fetch or an unresolved merge
     candidate stays fail-closed.
   - `review_completeness trigger-bot` lists no flagged bot with a qualifying review in `trigger_bots[]` or `required_stale_bots[]`.

   *Done when:* each of these fails at `15aae32c6`: a fixture with the flagged bot in `stale_participants`, a qualifying review on an
   earlier head and no pending finding yields participation complete; the same fixture through `trigger-bot` yields an empty
   `trigger_bots[]` and `required_stale_bots[]`. These hold at `15aae32c6` and must keep holding: the same fixture with one pending
   finding is not complete; the same stale-bot fixture for a bot WITHOUT the flag stays `participated_stale` and is listed; a flagged
   bot whose only record is a refusal, an acknowledgment or a skip notice is not done (`refused` / `absent` as today); an unreadable
   fetch is not complete.

2. **No path posts or awaits a CodeRabbit trigger once the review is on record.**
   - `github_re_review.py` `_ReReviewStrategy.request_fresh_review` (L1147-1215, the one post chokepoint, guarded today by the rate window
     alone) refuses for a flagged bot whose qualifying review is on record on this pull request, returns a named refusal and posts nothing.
   - `resolve_recovery_action` (L1037-1050) does not return `generate_trigger` with `claim_window_elapsed_review_on_record` for a
     flagged bot; the elapsed-window arm with a review on record settles without a post.
   - `automatic-review/SKILL.md` trigger B (L215-319, including the sentence at L36 and L224 that a required stale bot is triggered
     "whatever the gate says" and the step-done guard remedy near L1349-1366) and trigger A
     (`phase-6-finalize/standards/branch-cleanup-rereview.md`, L13 and the loop at L148-159) post and await nothing for a flagged bot
     with a review on record. `re_review_on_branch_cleanup` and `re_review_on_loopback` keep their meaning for every other bot.
   - `runbook-lane/SKILL.md` section 6 step 6 (L795-796, "after every push, re-trigger a reviewer whose last review predates the
     head") and the merge-of-base paragraph (L886-887) leave a flagged bot out of the re-trigger.

   *Done when:* each of these fails at `15aae32c6`: `request_fresh_review` for the flagged bot with a credited review on record and an
   expired window returns the named refusal and the post stub is not called; `resolve_recovery_action` for the flagged bot with
   `review_on_record` credited or stale and an elapsed window returns an action that posts nothing; a doc-contract test finds the done
   rule in trigger B, trigger A and the lane's section 6 step 6, and finds the "triggered whatever the gate says" sentence bound to a bot
   without the flag. These hold at `15aae32c6` and must keep holding: a flagged bot with NO review on record is triggered once and
   follows the quota policy (the escalated command once, close-and-reopen only with no review); an unflagged bot with a stale review
   is re-triggered by trigger B exactly as today.

3. **The merge gates accept a done review without a review of the head.**
   - `phase-6-finalize/scripts/pre_merge_gate.py` `_check_participation` and `_participation_verdict` (L855-1076, L1115-1196) allow a
     merge when the flagged required bot's qualifying review is handled, with no `review-barrier-gap` authorization, and still refuse
     on a pending finding, an unreadable state or an unresolved merge candidate. `_head_binding_refusal` (L457-600) is not weakened: the
     automatic-review step still re-fires when the head advances, and that re-fire completes without posting a trigger for a done bot.
   - `phase-6-finalize/standards/branch-cleanup.md` Predicate 2 (L1006-1040) reads the same verdict.
   - `runbook-lane/SKILL.md` section 7 (L817-833, L858-866, L868-876): "every required reviewer reviewed the current head" is satisfied
     for a flagged reviewer by done; the standing authorization's post-push re-trigger condition no longer applies to it; the
     "which head it last reviewed" fact states the head the one review covered. `review-gate` is unchanged and still never overridden.
   - `runbook_lane.py`: where `resolve` emits `quota_limited` for the reviewer rows (three hits), it also emits the flag, so the lane
     reads one source. HYPOTHESIS on the exact rows (verify-at-outline).

   *Done when:* each of these fails at `15aae32c6`: `pre_merge_gate` with the flagged required bot's qualifying handled review on an earlier
   head, the head advanced by a fix commit and no authorization allows the merge (today `merge_participation_unproven`); a lane
   doc-contract test finds section 7 satisfied by done for a flagged reviewer. These hold at `15aae32c6` and must keep holding: the
   same fixture with a pending finding is refused; the same fixture for an unflagged bot is refused; `merge_candidate_not_gated` still
   refuses a head-dependent step record whose head moved and is not waived; `review-gate` has no head-currency condition and answers
   `false` on an unresolved thread; the lane's gate for a reviewer with NO qualifying review is unchanged.

4. **The prose and the pins say the same thing.** Every document that states the old re-review or currency behaviour for CodeRabbit states
   the done rule instead, and every test that pinned the old behaviour is moved to the new behaviour, never deleted without a
   replacement. `coderabbit.md` L428-431 ("nothing about a spent quota is a reason to merge without the review") is scoped to the
   no-review case.

   *Done when:* the documentation and contract tests listed under Expected Surface pass on the changed documents and fail on a planted
   copy of the old sentence (a control for each pinned document family); no document outside the surface states that a stale CodeRabbit
   review is re-triggered.

Split guard: four deliverables, one rule. D1 is the state, D2 the requests, D3 the gates, D4 the sweep; none ships alone because a
requests-only change leaves the gates refusing and a gates-only change leaves the requests posting.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- The rule is data: one registry flag read through `bot_registry.py`, never a bot-name test in a consumer. A new flag is documented in
  the bot-participation contract's data-block table and read by one accessor.
- The producer keeps reporting the facts it reports today (`stale_participation_bots[]`, `review_on_record`); the done rule is applied
  where the verdict is formed, once, so the FIND guard, the merge dispatch and the lane agree.
- Fail closed: an unreadable fetch, an unresolved merge candidate, an unscoped finding row and an undecidable review state are never
  done.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture and are shown red where the Done-when says so. A doc-pin test that
  fails because a document legitimately changed is moved, not weakened.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `runbook-lane/SKILL.md` re-triggers after every push (L795-796), re-triggers after merging the base (L886-887), requires "every required reviewer reviewed the **current head**" with the quota-limited standing authorization needing a post-push re-trigger (L817-833), and states the quota policy applies only while no qualifying review exists (L858-860)
- OBSERVED: `automatic-review/SKILL.md` trigger B joins `stale_participation_bots[]` with the stored-finding bots (L219-222) and triggers a REQUIRED stale bot whatever `re_review_on_loopback` says (L224, L279-286, frontmatter L34-36); `re_review_on_branch_cleanup` defaults to true (L37-39)
- OBSERVED: `github_re_review.py` `resolve_recovery_action` returns `generate_trigger` / `claim_window_elapsed_review_on_record` for a requires-explicit-trigger bot whose review on record is credited or stale (L1037-1050)
- OBSERVED: `review_completeness.classify_bot` returns `STATE_PARTICIPATED_STALE` for a bot in `stale_participants` (L963-964)
- HYPOTHESIS: `request_fresh_review` (`github_re_review.py` L1147-1215) is the only site that posts the trigger comment and its only guard is the rate window (grounding leaf read; confirm at outline by reading every `post_pr_comment` caller)
- HYPOTHESIS: trigger A (`branch-cleanup-rereview.md` L13, L148-159) re-requests the review on a rebased head even when the pre-rebase tree was reviewed (grounding leaf read)
- HYPOTHESIS: `pre_merge_gate._participation_verdict` allows only complete participation or a known gap with an admissible `review-barrier-gap` authorization at the head, and a `participated_stale` required bot is refused (L1115-1196, docstring L1145-1151; grounding leaf read)
- HYPOTHESIS: `review-gate` (`runbook_lane.py cmd_review_gate`) has no head-currency condition, so the lane's currency demand is prose only (`runbook-lane/SKILL.md` L198-212; grounding leaf read, confirm by reading the verb)
- HYPOTHESIS: the finalize path has no "one handled review authorizes the merge" branch at all, the lane's standing authorization being the only one (grounding leaf read)
- HYPOTHESIS: the automatic-review re-fire on a head advance (`head_dependent: true`, `--head-at-completion`) can complete without a trigger once classify reads the bot as done; if the re-fire path itself posts a trigger, that is part of D2 (verify-at-outline in `automatic-review/SKILL.md` L1261 and the `ci barrier` re-settle)
- HYPOTHESIS: CodeRabbit's finished-review marker names a commit (`coveredCommitId` / `sourceCommitId`), so "a qualifying review on one of this pull request's heads" is decidable from the marker; PLAN-LB-132 made an edit that names no commit credit nothing, so confirm that a real CodeRabbit review comment still names one (`coderabbit.md` L343-385)
- HYPOTHESIS: an auto-review CodeRabbit performs without being asked (the registry declares `requires_explicit_trigger`, the bot's central configuration is outside the repository) is ingested like any comment and never reopens done

## Questions the Plan Must Settle at Outline (decisions, not forks — record the answer in the PR)

- Whether a clean review with no finding (`participated_but_empty`) is a qualifying review (this spec says yes: it names a head and a marker).
- Whether the flag name and its accessor sit beside `participation_requires_update` in the registry data block and the contract's table.
- Whether `pre_merge_gate` needs a new named verdict or reuses `participated` (this spec prefers reuse, so the merge dispatch, the FIND guard and the lane cannot disagree).
- Whether `re_review_on_loopback` and `re_review_on_branch_cleanup` need any change beyond their descriptions (this spec says no: they keep their meaning for an unflagged bot).
- Whether close-and-reopen, which changes the pull request number, resets done (this spec says yes — done is per pull request number — and the case arises only when no review existed, so nothing is lost).

## Expected Surface

Source:

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — `classify_bot`, `check_completeness`, the `trigger-bot` selector (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — the registry data block, the re-review table row (L142), L400-415, L428-441, L470-479, the § Re-review (D1, D2, D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` — the flag and its accessor (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — frontmatter knob descriptions (L34-45), trigger B (L215-319), Branch 4 and the step 3 post (L839-858, L916-926), the guard remedy (L1349-1366) (D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` — `resolve_recovery_action`, `request_fresh_review` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py` — `_check_participation`, `_participation_verdict`, the docstring at L1145-1151 (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup-rereview.md` and `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — trigger A, Predicate 2 (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — section 6 step 6 and step 7, section 7 (D2, D3, D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — the `resolve` rows that carry `quota_limited` (D3; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` and `_github_pr.py` — only if the producer must report which bot holds a qualifying review (D1; prefer no change)

Documentation (D4; HYPOTHESIS until each is read at outline):

- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
- `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md`
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-review-operations.md` and `api-contract.md`
- `marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/standards/automated-review-lifecycle.md`
- `doc/user/configuration.adoc`, `doc/user/parallelism-and-locking.adoc`, `doc/user/getting-started.adoc`, `doc/concepts/planning-workflow.adoc`

Tests (move or add; the first six were read by the grounding leaf, the rest are HYPOTHESIS sized by search hits):

- `test/plan-marshall/automatic-review/test_trigger_b_stale_set_from_participation.py`
- `test/plan-marshall/automatic-review/test_review_policy_defaults.py`
- `test/plan-marshall/automatic-review/test_review_completeness_state.py`
- `test/plan-marshall/workflow-integration-github/test_re_review_strategy_fresh_review.py`
- `test/plan-marshall/phase-6-finalize/test_pre_merge_gate.py`
- `test/plan-marshall/runbook-lane/test_runbook_lane_review_gate.py`
- HYPOTHESIS: `test/plan-marshall/workflow-integration-github/` (`test_re_review_strategy_await.py`, `_cli.py`, `_match.py`, `_resolve.py`, `test_github_pr_currency.py`, `test_refusal_recovery_arming_axes.py`, `test_re_review_doc_predicate_parity.py`)
- HYPOTHESIS: `test/plan-marshall/automatic-review/` (`test_recovery_route_table_totality.py`, `test_no_unreviewed_commit_step_contract.py`, `test_review_currency_holes_regression.py`, `test_structural_refusal_consumer_docs.py`, `test_bot_participation_contract_*`, `test_review_completeness_{cli,verdicts,overlays,evidence}.py`)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/` (`test_branch_cleanup_merge_queue_routing_*.py`, `test_lb55_merge_head_binding.py`, `test_review_merge_invocation_contract_*.py`)
- HYPOTHESIS: `test/plan-marshall/runbook-lane/test_runbook_lane.py`, `test/plan-marshall/manage-config/test_config_defaults.py`

## Dependencies and Sequencing

- Depends on: PLAN-LB-132 (shipped, `3ed0888ea`) — it rewrote the surfaces this plan reads (`review_completeness.py`, `automatic-review/SKILL.md`, `coderabbit.md`, `github_pr.py`, `pre_merge_gate.py`, `runbook_lane.py`); it is in the base.
- Overlaps with: PLAN-LB-138 on `runbook_lane.py` if D3 touches it (one file, no prompt under the disjointness rule); PLAN-LB-133 touches `phase-6-finalize/workflow/` documents and shares no file with the `phase-6-finalize/standards/` files named here; the gate decides.
- Adjacent to: the PLAN-LB-132 residue (a `manage-findings` verb that stamps a pull request onto a findings row is not in scope), the PLAN-LB-128 Watch items on `github_pr.py` (heading drift, scalar-typed registry field), and the operator-owed second-machine and executor items.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-142-coderabbit-review-done-after-handling.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
