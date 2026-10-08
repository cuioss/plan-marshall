# PLAN-LB-19: The review gate credits only a review of the commit being merged

epic: live-blockers
workstream: WS-05

> ⛔ **SUPERSEDED — do not launch.** Regrouped on 2026-10-08: PLAN-LB-24 (all deliverables).
> This file is kept as the audit record of the original cut. The successor carries its
> deliverables, claim labels and surface entries unchanged.

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-19-review-gate-currency.md` and is queued as one row file,
> `queue/PLAN-LB-19.json`, in the epic ledger. The orchestrator EMITS the command below; it
> never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

After a fix commit, a required review bot whose only comment predates the new HEAD is correctly
reported `participated_stale`, but nothing re-triggers it: the re-trigger picks its bots from stored
findings, and a bot whose comment was filtered as noise has none. The step loops until the operator
re-runs it by hand and forces the step record (PR #1690). In the other direction the gate can pass on
a review of an older commit: the helper that compares the commit a bot says it reviewed with the merge
HEAD has no production caller, and a bot that posts a new comment per review is never tested against
the merge commit at all. Separately, triage tells the reviewer a finding is fixed and resolves the
thread before any commit or build exists (PR #1704, about 25 minutes early). This plan makes the
re-trigger reach every stale required bot, wires or removes the commit comparison, closes the
untested path for bots that post per review, and moves the "fixed" reply behind the fix commit.
Carries forward review-apparatus PLAN-PR-069 D1 and PLAN-PR-070 D0, D5 and D6 (bodies in PLAN-PR-045
§ D0–D2 and PLAN-PR-053 § D2), process-compliance PLAN-24 D2 (the re-trigger half), and lessons
`2026-10-03-18-001` and `2026-10-07-07-008`.

## Deliverables

1. **The re-trigger after a fix commit selects every stale required bot, whether or not it has a
   stored finding.** Trigger B builds its stale set from the bots' participation state at the
   current HEAD — the `stale_participation_bots[]` the producer already returns, or the
   `bot_states` of `review_completeness check` — joined with the bots that have stored findings.
   `review_completeness trigger-bot` returns the full list of bots to trigger, required bots first,
   and the step calls `github_re_review re-review` once per listed bot before the buffer wait. When
   the step-done guard finds a required bot on `participated_stale`, the loop-back it records leads
   to that trigger on re-entry even if `re_review_on_loopback` is `false`; a plain re-dispatch must
   not reach the same state again.
   *Done when:* a test in `test_review_completeness_cli.py` calls `trigger-bot` with a required bot
   that is stale and has no stored finding and asserts it is in the returned list (fails before: the
   verb only sees `--stale-bots` built from findings); a test with two stale bots asserts both are
   returned; a doc-contract test asserts the trigger-B section of `automatic-review/SKILL.md` reads
   the stale set from participation state; on a PR where the in-house reviewer's only comment
   predates a fix commit, the step posts `/review` on re-entry without `--force` on any step record.

2. **The commit comparison is called in production, or it is deleted.** `bot_claimed_sha_matches_head`,
   `carry_currency_verdict_to_check_state` and the `currency_current` parameter of
   `_derive_overall_status` exist with tests and no caller. Either route: (a) wire them — in the
   participation loop of `fetch_findings`, a comment that names a commit is current only when that
   commit is the merge candidate, and stale when it names another, whatever its timestamps or edit
   history say; a comment naming no commit keeps today's ledger rules; the verdict reaches the checks
   surface through `currency_current`; or (b) delete the three and the test that pins them, and say
   in the contract that currency is decided by the ledger alone. The plan picks one and records why.
   Under (a) the two commit recognisers (`_SHA_TOKEN` in `_github_pr.py`, full 40 characters only;
   `_COMMIT_SHA_TOKEN_RE` in `github_re_review.py`, 7 to 40) become one.
   *Done when:* a search for each of the three names under `marketplace/bundles/` finds at least one
   call site outside its own definition, or finds nothing at all; under (a), a test in
   `test_github_pr_currency.py` gives a comment that was edited after the last credit and names the
   previous HEAD, and asserts the bot lands in `stale_participation_bots[]` (fails before: the fresh
   edit credits it), with a control where the comment names the merge candidate and is credited on
   first sight.

3. **A bot that posts a new comment per review is tested against the merge commit too.** Sourcery
   declares `participation_requires_update: false`, so one review body from before a fix commit keeps
   crediting it at every later HEAD. The contract's stated reason for leaving this open is that such
   comments carry no reviewed commit; a GitHub review does carry one (`commit_id`), and
   `fetch_pr_reviews_with_commits` already reads it. For the `review_body` shape, credit only a
   review whose commit is the merge candidate; report an older one as `participated_stale` with the
   re-trigger as the remedy. The contract section "The currency-blind path for append-per-review
   bots" is rewritten to describe what is now tested and what still is not.
   *Done when:* a test in `test_github_pr_currency.py` feeds a Sourcery review body whose review
   commit is the previous HEAD and asserts Sourcery is in `stale_participation_bots[]` and not in the
   participated set (fails before); a control with the review commit equal to the merge candidate
   credits it; the set of bots affected is printed by the test from `bot_registry` rather than
   written into it; `test_bot_participation_contract_*.py` pass against the rewritten section.

4. **"Fixed" is posted only once the fix commit exists.** Today triage resolves a finding `fixed`
   and the respond loop in the same dispatch posts the reply and resolves the thread, before the fix
   task has run. `post_responses` holds back a `fixed` disposition until the finding carries the
   commit that fixed it and that commit is an ancestor of the PR head; the reply names the short
   commit id; the thread is resolved in the same call. Until then the finding is listed in the
   return as `deferred_until_commit` and no reply goes out — or, if the plan chooses, a neutral
   "being addressed" reply is posted once and the thread stays open. Declined, suppressed and
   accepted dispositions are transmitted as they are today. The step that commits the fix stamps the
   commit on the finding, and the respond loop runs again after the push.
   *Done when:* a test in `test_comments_stage_post.py` runs `post_responses` over a `fixed` finding
   with no fix commit and asserts no thread reply, no resolve call and one `deferred_until_commit`
   row (fails before: it replies and resolves); a second run after the commit is stamped posts a
   reply containing the short commit id and resolves the thread; a `rejected` finding in the same
   store is transmitted on the first run; `triage.md` and `verification-feedback.md` state the
   ordering, and the inline-fix variant described in lesson `2026-10-07-07-008` is either documented
   as allowed under the same rule or forbidden outright.

## Claim Labels

- OBSERVED: trigger B collects its stale set as "the distinct non-empty `bot_kind` values across ALL staged findings" and skips the whole section when no bot-authored finding exists — read at `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` § "Re-review after a loop-back fix commit (trigger B)" step 1
- OBSERVED: `select_stale_bot_for_trigger` returns ONE bot, chosen only from the list it is handed, and falls back to the newest finding's bot when that list is empty — read at `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` § `select_stale_bot_for_trigger`
- OBSERVED: trigger B is skipped entirely when `re_review_on_loopback` is `false` (the default), and the step-done guard's remedy text for `participated_stale` names "the `re_review_on_loopback` path above" — read at `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` § trigger B and § "Step-done participation guard (D3)"
- OBSERVED: the producer already computes the stale set independently of stored findings and returns it as `stale_participation_bots[]` — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` § `cmd_fetch_findings` (the `stale_participation` dictionary in the participation loop)
- OBSERVED: `bot_claimed_sha_matches_head` and `carry_currency_verdict_to_check_state` are referenced only by their own definitions and by `test/plan-marshall/automatic-review/test_review_currency_holes_regression.py`; every caller of `_derive_overall_status` omits `currency_current` — searched across `marketplace/`, `test/`, `.claude/` and `.github/`; call sites read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` and `_github_ci.py`
- OBSERVED: the currency test runs only for bots with `participation_requires_update: true`; for any other bot the loop credits on the first admissible comment and skips the rest — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` § `cmd_fetch_findings` (`if _bot_kind in participated and not _requires_update: continue`, and the `_requires_update and not _reviewed_at_merge_candidate(...)` guard)
- OBSERVED: of the three registered bots only Sourcery declares `participation_requires_update: false`; CodeRabbit and the in-house reviewer declare `true`. An earlier spec counted CodeRabbit on the untested side; that is no longer so — read at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md`, `coderabbit.md` and `cuioss-review-bot.md` § "Registry data block"
- OBSERVED: the contract records the untested path as an accepted gap and names what reopens it: a required bot of this kind "observed satisfying the quorum on a merge candidate it demonstrably did not review" — read at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md` § "The currency-blind path for append-per-review bots — an accepted, bounded gap"
- OBSERVED: the comment fetch used by `fetch_findings` builds `review_body` records without the review's commit, while the separate reviews fetch returns `commit_sha` from the REST `commit_id` — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` § `fetch_pr_comments_data` and `_github_pr.py` § `fetch_pr_reviews_with_commits`
- OBSERVED: every stored finding is stamped with the PR head read at fetch time (`reviewed_commit_sha = _github.fetch_pr_head_sha(pr_number)`), not with the commit the comment reviewed — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` § `cmd_fetch_findings`
- OBSERVED: triage resolves a FIX finding as `fixed` at the moment it allocates the fix task, `fixed` is one of the resolutions `post_responses` transmits, and a thread-bearing finding gets a reply and then a resolve-thread call — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` § 3c FIX, `github_pr.py` § `_RESPONDABLE_RESOLUTIONS` and § `cmd_post_responses`
- OBSERVED: the respond loop runs as Step 8 of the same dispatch that triaged, before the loop-back that executes and commits the fix — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md` § "Step 7: Loop-back signalling" and § "Step 8: Respond loop"
- OBSERVED: the reply text triage prescribes is "Will be addressed by TASK-{N}; see follow-up commit on this branch", which is future tense; the wording "Fixed in a follow-up commit" came from a dispatch that fixed inline against the documented FIX contract. The thread is resolved early on both paths — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` § 3c and lesson `2026-10-07-07-008`
- OBSERVED: `_match_review` has no author gate by design ("the SHA match already establishes provenance"), so a wait for one bot's review is satisfied by any author's review of that commit submitted after the trigger — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` § `_ReReviewStrategy._match_review`
- HYPOTHESIS: a bot's reply inside an old review thread, posted after a fix commit, is credited as a fresh review: it is an `inline` comment, a declared evidence shape for CodeRabbit, has no ledger row and does not predate the commit, so the first-observation arm credits it — confirm/refute at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` § `_reviewed_at_merge_candidate` and § `_is_participation_evidence` with a fixture (verify-at-outline)
- HYPOTHESIS: a finding record has no field for the commit that fixed it, so deliverable 4 adds one and a writer for it — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` § `resolve` and the `responded` marker (verify-at-outline)
- HYPOTHESIS: Sourcery is a required bot in at least one consumer repository, so deliverable 3 changes a merge verdict outside this repository; here it is optional (`.plan/marshal.json` lists `required_bots: cuioss-review-bot,coderabbit`) — confirm/refute by reading `.plan/marshal.json` in each consumer checkout under `/Users/oliver/git/` (verify-at-outline)
- HYPOTHESIS: the in-house reviewer's comment names its reviewed commit as a permalink holding the full 40-character id, so `bot_claimed_sha_matches_head` can read it as written — confirm/refute at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md` § "Participation evidence" and one live comment (verify-at-outline)
- Verify-first clause: PLAN-LB-18 edits the same trigger-B section and `github_re_review.py`. Read what it shipped first: if acknowledgment comments are now excluded from the answer path, deliverable 1's per-bot loop must use the same return fields.
- Verify-first clause: deliverable 3 changes when a bot counts toward the quorum. Before implementing, publish the list of bots it affects (derived from the registry) and the consumer repositories that require one of them, and get the operator's go-ahead. Without it, ship deliverable 3 as disclosure only — a field in the `fetch_findings` return naming each credited bot whose evidence predates the merge commit — and leave the verdict unchanged.
- Verify-first clause: deliverable 4 must not strand a reply. Enumerate every path that ends a plan after a `fixed` disposition without a fix commit (fix task dropped, plan abandoned, finding re-resolved) and state what the reviewer sees on each.

## Expected Surface

- DERIVED — this spec is superseded and claims no surface of its own. The entries it declared are
  recorded in the next section and are now declared by the successor named in the banner above.

## Superseded Surface (record only)

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — trigger B stale-set derivation and per-bot loop; step-done guard's `participated_stale` remedy
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — `select_stale_bot_for_trigger`, `cmd_trigger_bot`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md` — § "The currency rule" and § "The currency-blind path for append-per-review bots"
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md` — § "Participation evidence"
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — participation loop in `cmd_fetch_findings`, `_reviewed_at_merge_candidate`, `cmd_post_responses`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — `bot_claimed_sha_matches_head`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_checks.py` — `carry_currency_verdict_to_check_state`, `_derive_overall_status`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` — review commit on `review_body` records; `_derive_overall_status` call site
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` — the second commit recogniser
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md` — `fetch_findings` and `post_responses` return fields
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md` — Step 8 ordering
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` — § 3c FIX reply text and the inline-fix rule
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — item 7c: a second respond pass after the fix commit is pushed
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — a fix-commit field on a finding (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py` — the same hold-back in the GitLab `post_responses`, if that verb shares the selection rule (verify-at-outline)
- OBSERVED: `test/plan-marshall/automatic-review/test_review_completeness_cli.py` — `trigger-bot` cases
- OBSERVED: `test/plan-marshall/automatic-review/test_review_currency_holes_regression.py` — the helper tests, kept or removed with the helpers
- OBSERVED: `test/plan-marshall/automatic-review/test_bot_participation_contract_surface.py` — contract text pins
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr_currency.py` — commit-comparison and per-review-bot cases
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_comments_stage_post.py` — the held-back `fixed` reply
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier_members.py` — a stale per-review bot blocks at the barrier
- OBSERVED: `test/plan-marshall/plan-marshall/test_verification_feedback_producer_vocab.py` — workflow document pins

## Dependencies and Sequencing

- Depends on: PLAN-LB-18 (CodeRabbit quota recovery). It owns refusal and acknowledgment recognition in the files this plan edits; classifying staleness on top of an answer path that still reads an acknowledgment as a decline would re-trigger bots for the wrong reason.
- Overlaps with: PLAN-LB-18 on `automatic-review/SKILL.md`, `github_re_review.py`, `github_pr.py` and `_github_pr.py`; PLAN-LB-05 on `automatic-review/SKILL.md` (poll pacing); PLAN-LB-06 on `plan-marshall/workflow/triage.md` (fix-task creation); PLAN-LB-08 on `manage-findings/scripts/_findings_core.py`; PLAN-LB-09 on the pre-merge check in `branch-cleanup.md`, which this plan reads and does not edit. Sequence after each that is in flight.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup-rereview.md` (trigger A, after the pre-merge rebase). It triggers every participating bot already and is not changed.
- Adjacent to: the seven `ext-triage-*/standards/pr-comment-disposition.md` files, which describe FIX as "thread reply linking commit". They already state the intended outcome and are not edited.
- Left out on purpose: (1) storing the commit a review covered separately from the head at which it was fetched, so a re-fetch stops re-stamping old findings (PLAN-PR-053 § D2) — it changes the findings schema and every reader of `reviewed_commit_sha`; (2) refusing to credit a bot's reply inside an old thread as a fresh review (PLAN-PR-070 D2, fourth class) — carried above as a hypothesis to confirm, not fixed here; (3) an author gate on the review arm of the re-review wait, so one bot's wait cannot be satisfied by another author's review (PLAN-PR-070 D6); (4) the in-house reviewer's first clean review, which has no commit link to verify against (lesson `2026-09-19-21-001`).
- Operator decision needed: deliverable 3 — whether a bot that posts per review may lose its credit when its review predates the merge commit, in every repository that requires such a bot. Deliverable 2 — wire or delete; the plan may decide and report.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-19-review-gate-currency.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
