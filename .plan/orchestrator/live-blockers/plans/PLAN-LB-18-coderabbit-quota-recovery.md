# PLAN-LB-18: CodeRabbit quota recovery that can finish, and reads the bot's notices correctly

epic: live-blockers
workstream: WS-05

> ⛔ **SUPERSEDED — do not launch.** Regrouped on 2026-10-08: PLAN-LB-24 (all deliverables).
> This file is kept as the audit record of the original cut. The successor carries its
> deliverables, claim labels and surface entries unchanged.

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-18-coderabbit-quota-recovery.md` and is queued as one row file,
> `queue/PLAN-LB-18.json`, in the epic ledger. The orchestrator EMITS the command below; it
> never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

When CodeRabbit refuses a review for quota, the `plan-marshall:automatic-review` step starts a wait of
up to an hour inside a dispatched agent whose whole budget is 15 minutes and whose pacing instruction
is a foreground `sleep` the harness rejects. The step can therefore never finish its own recovery: the
operator kills it and re-dispatches, and each attempt spends one of the six recovery attempts the PR
has. Around that wait, the step misreads four of the bot's ordinary messages: it finds no reset time in
"Next included review available in N minutes" and falls back to an hour, it records a "Review
triggered" acknowledgment as a decline and offers "merge anyway" while the review is running, it has
no way to send `@coderabbitai full review` (the only command the bot accepts when no new commit
exists), and it misses a refusal that arrives as an edit of an older comment. This plan moves the wait
to the orchestrator, where it can run and be seen, and fixes the four readings. Carries forward
process-compliance PLAN-24 D1–D3 and review-apparatus PLAN-PR-069 D2, D3, D4 and D6 (bodies in
PLAN-PR-043 § D2, § D6, § D7 and PLAN-PR-052 § D1, § 3a).

## Deliverables

1. **The rate-window wait is handed back to the orchestrator and has a visible state.** After a
   successful `rate-window claim` (Branch 2 of § "Rate-limit refusal recovery"), the dispatched step
   stops and returns an `escalate_ask`-class envelope with a new reason (for example
   `rate_window_await`) carrying `bot_kind`, `pr_number`, the claim's expiry instant, the remaining
   seconds and the `rate_window_arming[]` row. It issues no `sleep` and does not poll the claim.
   `phase-6-finalize` item 7a consumes that reason without asking the operator: it waits in the main
   context until the claim expires plus the jittered delay from `merge_lock poll-delay`, then
   re-dispatches the step, which finds the window expired and goes straight to the re-consult that
   selects Branch 4 or Branch 5. The wait is one bounded script call per segment that fits the host
   Bash ceiling, or the `await-long-running` detach seam with a new consumer value; the plan picks
   one and states why. While it waits, the plan's terminal title and work log name the bot and the
   expiry time. The budget `review_rate_window_timeout_seconds` still bounds the total wait and still
   ends in `escalate_ask{reason: rate_window_timeout}`.
   *Done when:* a doc-contract test fails if `automatic-review/SKILL.md` prescribes a standalone
   `sleep` anywhere in § "Rate-limit refusal recovery", and passes after the change; a second test
   pins that item 7a's reason list contains the new reason and routes it to a wait rather than to
   `AskUserQuestion`; and a run on a PR with a live quota refusal completes the recovery with no
   operator re-dispatch (record the run's work-log lines in the PR description).

2. **The reset time CodeRabbit actually states is extracted, and an unreadable one is reported.**
   `rate_limit_eta_patterns` in `coderabbit.md` gains the form "Next included review available in
   N minutes" (and its hour and "N minutes and M seconds" variants). Branch 2's
   `--window-seconds` conversion moves out of prose into a script result so that "38 minutes" becomes
   2280 without the agent doing arithmetic. When a recognised quota refusal yields no reset time, the
   refusal record says so in a field of its own (`eta_extracted: false`) instead of an empty string
   the caller cannot tell from "notice stated none".
   *Done when:* `_extract_rate_limit_eta` returns `38 minutes` for the notice body "Next included
   review available in 38 minutes." (fails before); a parametrised test feeds every refusal fixture
   body under `test/plan-marshall/workflow-integration-github/` through the extractor and fails if a
   body containing a digit followed by `minute`, `hour` or `second` yields an empty reset time; the
   window claimed for that notice is 2280 seconds, not 3600.

3. **An acknowledgment is neither a decline nor a finding.** CodeRabbit answers a trigger comment
   with "Action performed — Review triggered." and later "Action performed — Review finished.".
   Today `_ReReviewStrategy._match_bot_comment` accepts the first as the awaited answer; it names no
   commit, so `head_sha_verified` is `false` and the step records the bot as `declined`. The registry
   gains an acknowledgment list per bot; a matching comment is classified `acknowledged`, is never an
   eligible answer, and the await keeps polling. When `github_pr bot_completion` reports
   `in_progress: true` for that bot, a non-verifying comment match never produces `declined`.
   `fetch_findings` drops acknowledgment replies as noise alongside own-trigger comments, so they are
   not stored as `pr-comment` findings and not counted as false positives later.
   *Done when:* a test in `test_re_review_strategy_match.py` drives an acknowledgment comment posted
   after the trigger and asserts no match and no refusal record (fails before: the comment is
   returned as the match); a test in `test_comments_stage_filters.py` asserts both acknowledgment
   bodies are skipped as noise; a genuine short review comment from the same bot is still matched
   and still filed (negative control in both tests).

4. **"Nothing new to review" is its own condition, and its remedy can be sent.** CodeRabbit refuses
   `@coderabbitai review` on a commit it has already reviewed with "Already reviewed the last
   commit…" or "Review skipped — No new commits to review", inside the same "Action not completed"
   reply it uses for a quota refusal. Waiting does not change that answer; `@coderabbitai full
   review` does. The registry declares the escalated command beside `trigger_comment`
   (for example `full_review_trigger_comment`), `github_re_review re-review` gains a way to post it,
   refusal records carry a condition (`rate_limited` or `no_unreviewed_commit`), and
   `resolve_recovery_action` returns a new action for `no_unreviewed_commit` that posts the escalated
   command once instead of claiming a window. The refusal re-trigger guard in
   `request_fresh_review` still applies: no command is posted into an open window.
   *Done when:* a test feeds the two bodies above and a "Review rate limited" body through the
   refusal record and asserts two different conditions; `recovery-action` returns the new action for
   `no_unreviewed_commit` and `await_window` for `rate_limited`; a test asserts the string posted is
   the registry's escalated command; `test_recovery_route_table_totality.py` passes with the new
   action routed in `automatic-review/SKILL.md`.

5. **A refusal written as an edit of an older comment is seen, and an expired one is not treated as
   live.** `_detect_rate_limited_bots` picks each bot's newest comment by `created_at`, so when
   CodeRabbit rewrites its summary comment into a refusal, the detector keeps reading a different,
   newer-created comment and reports no refusal. The detector samples by the later of `updated_at`
   and `created_at`, the rule `_match_bot_comment` and `_detect_movement_bots` already use. Each
   `rate_limited_bots[]` record carries the instant the notice was last written. A notice whose
   stated window had already elapsed when it was read is reported with `stale: true`, and the
   recovery does not claim a window for it.
   *Done when:* a test in `test_pr_wait_for_comments_rate_limited_core.py` builds two comments by the
   same bot — an older-created one edited into a refusal after the newer one was posted — and asserts
   the bot is reported rate-limited (fails before); a second test gives a notice stating "12 minutes"
   and an `updated_at` two hours old and asserts `stale: true` and that `recovery-action` does not
   return `await_window` for it.

## Claim Labels

- OBSERVED: the step's whole budget is 900 s and the budget is stated to cover "the optional rate-window await" — read at `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` § "Timeout Contract"
- OBSERVED: the rate-window poll is paced with a standalone `sleep 60` Bash call for up to `review_rate_window_timeout_seconds` (default 3600), inside the dispatched step — read at `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` § "Branch 3 — poll the claimed window to expiry"
- OBSERVED: after the window expires the step is told to run a single `sleep {delay_seconds}` with a delay drawn from 5 to 20 minutes, which alone can exceed both the 600 s Bash ceiling and what is left of a 900 s budget — read at `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` § "The jittered wake boundary" and `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` § `poll-delay`
- OBSERVED: `phase-6-finalize` item 7a already consumes five `escalate_ask` reasons from this step and item 5d skips the completion guard on any `escalate_ask` return regardless of reason, so a sixth reason needs a 7a branch and no 5d change — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` § item 5d and § item 7a
- OBSERVED: a "leaves never wait" rule already exists as a standard and is contradicted by Branch 3 — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/waiting.md` § "The main loop owns waiting — leaves never do"
- OBSERVED: CodeRabbit's three `rate_limit_eta_patterns` all require the words "before requesting another review" or "before … limit resets"; none matches "Next included review available in N minutes" — read at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` § "Registry data block"
- OBSERVED: `_extract_rate_limit_eta` returns `''` when no pattern matches, and Branch 2 then omits `--window-seconds` so the claim uses the verb default — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` § `_extract_rate_limit_eta` and `automatic-review/SKILL.md` § "Branch 2"
- OBSERVED: `_match_bot_comment` treats every non-refusal comment by the awaited bot written after the trigger as eligible, and `_verifies_head_sha` then decides the verdict from the body; nothing classifies an acknowledgment — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` § `_ReReviewStrategy._match_bot_comment`
- OBSERVED: the strings "Review triggered", "Action performed", "Already reviewed", "No new commits", "Next included" and "full review" occur in no file under `marketplace/bundles/plan-marshall/skills/` that handles review bots (a recursive search found only unrelated prose hits) — searched at `marketplace/bundles/plan-marshall/skills/`, `test/plan-marshall/automatic-review/`, `test/plan-marshall/workflow-integration-github/`
- OBSERVED: `coderabbit.md` declares one `trigger_comment` (`@coderabbitai review`) and the registry reader exposes one trigger accessor — read at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` § "Registry data block" and `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` § `trigger_comment`
- OBSERVED: `_detect_rate_limited_bots` selects `max(bot_comments, key=created_at)` while `_detect_movement_bots` in the same file uses the later of `updated_at` and `created_at` — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` § `_detect_rate_limited_bots`, § `_detect_movement_bots`
- OBSERVED: the enumerative refusal arm is switched off (`UNRECOGNISED_REFUSAL_MAX_CHARS = None`), so a short bot comment that no pattern names is never classified as a refusal; it falls through to the answer path — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` § `UNRECOGNISED_REFUSAL_MAX_CHARS`
- HYPOTHESIS: the harness rejects a foreground `sleep` issued by a dispatched agent, so Branch 3 cannot run even for one minute; the evidence is a run report, not a read of the harness — confirm/refute at `.plan/orchestrator/process-compliance/inbox/archive/plan-12-tool-triage/plan-12-tool-triage-014.md` in the orchestrator ledger worktree and by one dry dispatch (verify-at-outline)
- HYPOTHESIS: the exact bodies of the acknowledgment and no-new-commit replies ("Action performed — Review triggered.", "Already reviewed the last commit. Use @coderabbitai full review …", "Review skipped / No new commits to review") are as the earlier specs quote them; no fixture at HEAD holds them — confirm/refute by reading the live comments on plan-marshall PR #1654 and one PR that drew the no-new-commit reply, then add them as fixtures in `test/plan-marshall/workflow-integration-github/_github_pr_fixtures.py` (verify-at-outline)
- HYPOTHESIS: `@coderabbitai full review` on an already-reviewed commit is accepted outside an open quota window and is itself counted against the quota; one observation supports the first half and none the second — confirm/refute against CodeRabbit's command documentation and the PR named in review-apparatus PLAN-PR-052 § Problem 1 (verify-at-outline)
- HYPOTHESIS: the main-context orchestrator can hold a wait of up to an hour through `await-long-running` with a new consumer value without changing that seam's two existing consumers — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/await-long-running.md` § "Parameters" and § "Recipe" (verify-at-outline)
- Verify-first clause: PLAN-LB-05 changes how waits are expressed in `automatic-review/SKILL.md` (the 30-second completion poll), `manage-locks/SKILL.md` and `await-long-running.md`. Read what it shipped before choosing between a bounded script wait and the detach seam for deliverable 1; use the same mechanism it introduced rather than a second one.
- Verify-first clause: decide whether the recovery attempt counter should be charged when the orchestrator re-dispatches after the wait. Today a successful claim spends one attempt (`--attempt-held true` exists for that reason); the re-dispatch must find the existing claim and not spend a second one. Confirm at `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` § `_run_rate_window_claim` (the `renewed` action) before writing the 7a branch.
- Verify-first clause: before adding any pattern, re-read the refusal-recognition tests for a control in both directions. A pattern that reads a genuine short review as an acknowledgment hides a finding; one that reads an acknowledgment as a review credits a review that has not happened. Each new list needs a positive and a negative fixture.

## Expected Surface

- DERIVED — this spec is superseded and claims no surface of its own. The entries it declared are
  recorded in the next section and are now declared by the successor named in the banner above.

## Superseded Surface (record only)

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — § "Rate-limit refusal recovery" Branch 2, Branch 3 and the jittered wake; § "Timeout Contract"; § "`escalate_ask` return"; trigger B's handling of an acknowledgment
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — reset-time patterns, acknowledgment list, escalated command, no-new-commit bodies
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md` — the acknowledgment class and the refusal condition are contract vocabulary
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` — accessors for the new registry fields
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — `_extract_rate_limit_eta`, `_detect_rate_limited_bots`, refusal record fields
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` — `_match_bot_comment`, `_refusal_record`, `resolve_recovery_action`, the escalated-command post
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — `fetch_findings` noise filter for acknowledgment replies
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md` — canonical invocations for `re-review`, `recovery-action` and `pr wait-for-comments` fields
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — item 7a branch for the new reason
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — a bounded wait or an expiry-instant field on `rate-window check`, if deliverable 1 takes the script route
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/SKILL.md` — canonical invocation for any changed `rate-window` verb
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/await-long-running.md` — a third consumer value, only if deliverable 1 takes the detach route (verify-at-outline)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_refusal_recovery_arming_eta.py` — reset-time extraction cases
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_re_review_strategy_match.py` — acknowledgment and no-new-commit cases
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_re_review_strategy_resolve.py` — the new recovery action
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_pr_wait_for_comments_rate_limited_core.py` — edited-comment sampling and the stale notice
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_comments_stage_filters.py` — acknowledgment replies dropped as noise
- OBSERVED: `test/plan-marshall/workflow-integration-github/_github_pr_fixtures.py` — new notice fixtures
- OBSERVED: `test/plan-marshall/automatic-review/test_bot_registry_patterns.py` — new registry fields parse
- OBSERVED: `test/plan-marshall/automatic-review/test_recovery_route_table_totality.py` — every recovery action has a branch in the skill
- OBSERVED: `test/plan-marshall/manage-locks/test_merge_lock_rate_window.py` — claim re-entry after the orchestrator wait
- HYPOTHESIS: `test/plan-marshall/automatic-review/test_rate_window_wait_leaves_the_leaf.py` — new doc-contract test for deliverable 1 (verify-at-outline)

## Dependencies and Sequencing

- Depends on: PLAN-LB-05 (unrunnable waits). It decides how a wait is expressed in a step document and owns the short `sleep 30` completion poll in the same skill file. Land it first and reuse its mechanism for the rate-window wait.
- Overlaps with: PLAN-LB-05 on `automatic-review/SKILL.md`, `manage-locks/SKILL.md` and `await-long-running.md`; PLAN-LB-19 on `automatic-review/SKILL.md` (trigger B), `github_re_review.py` and `github_pr.py`. Run the three one after another, never together. PLAN-LB-10 (`manage-status` step records) is adjacent: the stale-record facet of PLAN-24 D1 — `assert-step-recorded` reading an earlier attempt's record on retry — belongs there and is not repeated here.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup-rereview.md` (trigger A). It reads the same `re-review` return fields and gets the acknowledgment fix for free; its prose is not edited unless a field it names is renamed.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md` and `cuioss-review-bot.md`. The new registry fields default to empty for both; no pattern is added for either bot without an observed notice.
- Left out on purpose: turning the enumerative refusal arm on (it needs a measured threshold from a comment corpus); recognising the "Action not completed" wrapper by shape for bots other than CodeRabbit; the rate window as a per-attempt interval with a registry default (PLAN-PR-043 § D6 limbs beyond the hand-back); scoping `rate-window check` to its `--pr-number` (PLAN-PR-043 § D7); close-and-reopen re-stamping the `create-pr` record (PLAN-24 D4); the false-positive metric reading only the resolution enum (PLAN-24 D3, second half).
- Operator decision needed: none to start. If the live check of `@coderabbitai full review` shows it spends quota like any other trigger, the plan reports that and asks before making it automatic.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-18-coderabbit-quota-recovery.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
