# PLAN-LB-24: Automated review step: a completion poll that can run, CodeRabbit quota recovery that can finish, and a gate that credits only a review of the merge commit

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-24-review-step.md` and is queued as one row file, `queue/PLAN-LB-24.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Assembled on 2026-10-08 from PLAN-LB-05, PLAN-LB-18, PLAN-LB-19, which this spec supersedes in whole or in part.
> Deliverables, claim labels, surface entries and the carried sequencing notes are copied from those
> specs unchanged. Each deliverable is tagged with the spec and number it came from; inside carried
> text, "deliverable 2" or "D2" means that number of the SAME source spec, and a plan id below
> PLAN-LB-22 resolves through the id map at the end of § Dependencies and Sequencing.

## Objective

The `plan-marshall:automatic-review` step cannot wait and cannot tell a current review from an old one. Its completion poll and its quota recovery are paced with a foreground `sleep` the harness rejects, so the step is marked done while a bot is still reviewing or is killed and re-dispatched by hand; it misreads four ordinary CodeRabbit notices; a stale required bot with no stored finding is never re-triggered; and "fixed" is posted to the reviewer before a fix commit exists. This plan gives the poll a bounded script-side wait, hands the rate-window wait to the orchestrator, fixes the notice readings, makes the re-trigger reach every stale required bot, and holds the "fixed" reply until the commit is on the branch. The three sources are one plan because they edit the same step document and the same three scripts under `workflow-integration-github/scripts/`, and each later source names the earlier one as its prerequisite.

### Carried from PLAN-LB-05: Wait procedures the harness cannot run

Three finalize waits tell the agent to pace a poll with a standalone foreground `sleep`, which the
harness refuses, so the wait's budget is unreachable: the review-bot completion poll ended after a few
unpaced reads and the step was marked done while the bot was still reviewing; the merge-lock admission
wait and the merge-queue landing wait have the same shape. Two further waits mislead rather than block:
documents disagree on whether an orchestrator-tier build may run in the background, and a CI wait that
lapses while every check is still running is filed as a `ci_timeout` finding and costs a triage round.
This plan moves each short pacing wait into the script that owns the query (a bounded, script-side wait
the caller re-issues), states one runnable rule for long builds, and classifies a lapsed wait on a live
run as "still pending". Carries forward process-compliance PLAN-23 deliverable D4 (D4a, D4b) and the
remedy direction of truthful-signals PLAN-TRUTH-169 (folded recurrences) and PLAN-TRUTH-162 (D3, second
member).

### Carried from PLAN-LB-18: CodeRabbit quota recovery that can finish, and reads the bot's notices correctly

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

### Carried from PLAN-LB-19: The review gate credits only a review of the commit being merged

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

1. **[PLAN-LB-05 D3]** **The review-bot completion poll runs without `sleep`, and says what it saw.** `automatic-review`
   § "Completion-aware poll" paces `bot_completion` reads with `sleep 30`. Add a bounded wait to the
   `bot_completion` verb (for example `--wait-seconds` with an interval): it polls the bot's check-run
   until it completes or the bound lapses, and returns the existing `{status, in_progress, completed}`
   fields plus `timed_out` and the seconds waited; `no_check_name` and `unconfigured` return at once.
   The workflow re-issues the call until `review_completion_poll_timeout_seconds` is spent. When a
   bot is still in progress at that bound, the step records it in its `display_detail` and step
   record, not only in a WARNING log line. Done when: a test with a check-run that flips to completed
   on the third read returns `completed: true` from one call; a test with a check-run that never
   completes returns `in_progress: true, timed_out: true` after the bound; and the poll section holds
   no `sleep` instruction.

2. **[PLAN-LB-18 D1]** **The rate-window wait is handed back to the orchestrator and has a visible state.** After a
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

3. **[PLAN-LB-18 D2]** **The reset time CodeRabbit actually states is extracted, and an unreadable one is reported.**
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

4. **[PLAN-LB-18 D3]** **An acknowledgment is neither a decline nor a finding.** CodeRabbit answers a trigger comment
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

5. **[PLAN-LB-18 D4]** **"Nothing new to review" is its own condition, and its remedy can be sent.** CodeRabbit refuses
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

6. **[PLAN-LB-18 D5]** **A refusal written as an edit of an older comment is seen, and an expired one is not treated as
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

7. **[PLAN-LB-19 D1]** **The re-trigger after a fix commit selects every stale required bot, whether or not it has a
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

8. **[PLAN-LB-19 D2]** **The commit comparison is called in production, or it is deleted.** `bot_claimed_sha_matches_head`,
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

9. **[PLAN-LB-19 D3]** **A bot that posts a new comment per review is tested against the merge commit too.** Sourcery
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

10. **[PLAN-LB-19 D4]** **"Fixed" is posted only once the fix commit exists.** Today triage resolves a finding `fixed`
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

Carried in source order: bullets 1 to 4 from PLAN-LB-05; bullets 5 to 23 from PLAN-LB-18; bullets 24 to 44 from PLAN-LB-19.

- OBSERVED: the harness refuses a standalone foreground `sleep`; the documented `sleep 30` in the completion poll was refused on PR #1704 and the step was marked done with the bot still in progress — lesson `2026-10-07-07-007` (read through `manage-lessons get`), and the corpus's own rule at `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/tool-usage-patterns.md` § "No sleep for external waits", which forbids `sleep N` for external waits and says to extend the CI abstraction with a `wait-for-*` verb instead
  - verdict: unverifiable | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: tool-usage-patterns.md 'No sleep for external waits' holds as quoted (forbids sleep N, says extend CI wait-for-*); but manage-lessons get 2026-10-07-07-007 returns not_found and PR #1704 is a live PR
- OBSERVED: the completion poll prescribes `sleep {interval}` / `sleep 30` between `bot_completion` reads, and at the bound only logs a WARNING — `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:345`, `:351`, `:352-360`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: automatic-review/SKILL.md lines 345/351/352-360: pacing is a standalone `sleep {interval}` (30s) / `sleep 30` between bot_completion polls; budget exhaustion only logs a WARNING and moves on
- OBSERVED: `bot_completion` is a single read with no waiting form — `cmd_bot_completion` at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:2430-2524`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: github_pr.py cmd_bot_completion (2430-2524): one `gh pr checks` read returning {status,in_progress,completed}; no poll loop, no timeout/interval args on the bot_completion subparser
- HYPOTHESIS: no other finalize or execute document prescribes a standalone `sleep` outside the rate-window recovery owned by PLAN-LB-18 — confirm/refute with a content search for `sleep` across `marketplace/bundles/plan-marshall/skills/**/*.md` and `.claude/skills/**`, classifying each hit (verify-at-outline)
- OBSERVED: the step's whole budget is 900 s and the budget is stated to cover "the optional rate-window await" — read at `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` § "Timeout Contract"
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: automatic-review/SKILL.md 'Timeout Contract': FIND-only 15-minute (900 s) budget that 'covers the review-bot buffer, the completion-aware poll, the optional rate-window await, and the producer fetch_findings FIND'
- OBSERVED: the rate-window poll is paced with a standalone `sleep 60` Bash call for up to `review_rate_window_timeout_seconds` (default 3600), inside the dispatched step — read at `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` § "Branch 3 — poll the claimed window to expiry"
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: automatic-review/SKILL.md Branch 3: pacing is 'a single standalone sleep {interval}' (60s) / `sleep 60` up to review_rate_window_timeout_seconds (frontmatter default 3600), inside the dispatched step body
- OBSERVED: after the window expires the step is told to run a single `sleep {delay_seconds}` with a delay drawn from 5 to 20 minutes, which alone can exceed both the 600 s Bash ceiling and what is left of a 900 s budget — read at `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` § "The jittered wake boundary" and `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` § `poll-delay`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: SKILL.md 'jittered wake boundary' prescribes one `sleep {delay_seconds}`; merge_lock.py _DEFAULT_POLL_DELAY_MIN/MAX_SECONDS = 300.0/1200.0 (5-20 min), above the 600 s Bash ceiling and the 900 s budget
- OBSERVED: `phase-6-finalize` item 7a already consumes five `escalate_ask` reasons from this step and item 5d skips the completion guard on any `escalate_ask` return regardless of reason, so a sixth reason needs a 7a branch and no 5d change — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` § item 5d and § item 7a
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: phase-6-finalize/SKILL.md item 7a: 'Five escalation reasons reach this hook'; item 5d carve-out 'keys on status: escalate_ask alone ... covers every escalation reason uniformly' and names none
- OBSERVED: a "leaves never wait" rule already exists as a standard and is contradicted by Branch 3 — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/waiting.md` § "The main loop owns waiting — leaves never do"
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: plan-marshall/standards/waiting.md 'The main loop owns waiting - leaves never do': 'A dispatched leaf must not' hold a wait; automatic-review Branch 3 has the dispatched step poll up to 3600 s with sleep 60
- OBSERVED: CodeRabbit's three `rate_limit_eta_patterns` all require the words "before requesting another review" or "before … limit resets"; none matches "Next included review available in N minutes" — read at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` § "Registry data block"
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: coderabbit.md registry block: three rate_limit_eta_patterns, two ending 'before requesting another review', one 'before (?:the )?(?:rate )?limit resets'; none can match 'Next included review available in N minutes'
- OBSERVED: `_extract_rate_limit_eta` returns `''` when no pattern matches, and Branch 2 then omits `--window-seconds` so the claim uses the verb default — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` § `_extract_rate_limit_eta` and `automatic-review/SKILL.md` § "Branch 2"
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _github_pr.py _extract_rate_limit_eta ends `return ''` when no pattern yields a figure; SKILL.md Branch 2: 'omit the flag when the notice stated no ETA, so the claim falls back to the verb's default'
- OBSERVED: `_match_bot_comment` treats every non-refusal comment by the awaited bot written after the trigger as eligible, and `_verifies_head_sha` then decides the verdict from the body; nothing classifies an acknowledgment — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` § `_ReReviewStrategy._match_bot_comment`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: github_re_review.py _match_bot_comment: eligible = awaited-bot author, not _refusal_record, max(updated_at,created_at) > trigger_dt; _verifies_head_sha decides from body; no acknowledgment classifier exists
- OBSERVED: the strings "Review triggered", "Action performed", "Already reviewed", "No new commits", "Next included" and "full review" occur in no file under `marketplace/bundles/plan-marshall/skills/` that handles review bots (a recursive search found only unrelated prose hits) — searched at `marketplace/bundles/plan-marshall/skills/`, `test/plan-marshall/automatic-review/`, `test/plan-marshall/workflow-integration-github/`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: architecture search --content for the six strings over the 3496-file inventory: only hit is manage-execution-manifest/standards/decision-rules.md (unrelated); none in review-bot skills or the two test dirs
- OBSERVED: `coderabbit.md` declares one `trigger_comment` (`@coderabbitai review`) and the registry reader exposes one trigger accessor — read at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` § "Registry data block" and `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` § `trigger_comment`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: coderabbit.md registry block declares a single `trigger_comment: "@coderabbitai review"`; bot_registry.py exposes one accessor BotRegistry.trigger_comment(bot_kind) -> str plus its module-level wrapper
- OBSERVED: `_detect_rate_limited_bots` selects `max(bot_comments, key=created_at)` while `_detect_movement_bots` in the same file uses the later of `updated_at` and `created_at` — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` § `_detect_rate_limited_bots`, § `_detect_movement_bots`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _github_pr.py _detect_rate_limited_bots: `newest = max(bot_comments, key=lambda c: str(c.get('created_at') or ''))`; _detect_movement_bots compares max(updated_at, created_at) stamps against wait_start
- OBSERVED: the enumerative refusal arm is switched off (`UNRECOGNISED_REFUSAL_MAX_CHARS = None`), so a short bot comment that no pattern names is never classified as a refusal; it falls through to the answer path — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` § `UNRECOGNISED_REFUSAL_MAX_CHARS`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _github_pr.py: `UNRECOGNISED_REFUSAL_MAX_CHARS: int | None = None`; _is_unrecognised_refusal returns False first when threshold is None, so such a body is not a refusal and stays eligible as an answer
- HYPOTHESIS: the harness rejects a foreground `sleep` issued by a dispatched agent, so Branch 3 cannot run even for one minute; the evidence is a run report, not a read of the harness — confirm/refute at `.plan/orchestrator/process-compliance/inbox/archive/plan-12-tool-triage/plan-12-tool-triage-014.md` in the orchestrator ledger worktree and by one dry dispatch (verify-at-outline)
- HYPOTHESIS: the exact bodies of the acknowledgment and no-new-commit replies ("Action performed — Review triggered.", "Already reviewed the last commit. Use @coderabbitai full review …", "Review skipped / No new commits to review") are as the earlier specs quote them; no fixture at HEAD holds them — confirm/refute by reading the live comments on plan-marshall PR #1654 and one PR that drew the no-new-commit reply, then add them as fixtures in `test/plan-marshall/workflow-integration-github/_github_pr_fixtures.py` (verify-at-outline)
- HYPOTHESIS: `@coderabbitai full review` on an already-reviewed commit is accepted outside an open quota window and is itself counted against the quota; one observation supports the first half and none the second — confirm/refute against CodeRabbit's command documentation and the PR named in review-apparatus PLAN-PR-052 § Problem 1 (verify-at-outline)
- HYPOTHESIS: the main-context orchestrator can hold a wait of up to an hour through `await-long-running` with a new consumer value without changing that seam's two existing consumers — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/await-long-running.md` § "Parameters" and § "Recipe" (verify-at-outline)
- Verify-first clause: PLAN-LB-05 changes how waits are expressed in `automatic-review/SKILL.md` (the 30-second completion poll), `manage-locks/SKILL.md` and `await-long-running.md`. Read what it shipped before choosing between a bounded script wait and the detach seam for deliverable 1; use the same mechanism it introduced rather than a second one.
- Verify-first clause: decide whether the recovery attempt counter should be charged when the orchestrator re-dispatches after the wait. Today a successful claim spends one attempt (`--attempt-held true` exists for that reason); the re-dispatch must find the existing claim and not spend a second one. Confirm at `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` § `_run_rate_window_claim` (the `renewed` action) before writing the 7a branch.
- Verify-first clause: before adding any pattern, re-read the refusal-recognition tests for a control in both directions. A pattern that reads a genuine short review as an acknowledgment hides a finding; one that reads an acknowledgment as a review credits a review that has not happened. Each new list needs a positive and a negative fixture.
- OBSERVED: trigger B collects its stale set as "the distinct non-empty `bot_kind` values across ALL staged findings" and skips the whole section when no bot-authored finding exists — read at `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` § "Re-review after a loop-back fix commit (trigger B)" step 1
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: automatic-review/SKILL.md trigger B step 1: 'Collect {stale_bots} as the distinct non-empty bot_kind values across ALL staged findings'; 'If no bot-authored finding exists ... skip this section'
- OBSERVED: `select_stale_bot_for_trigger` returns ONE bot, chosen only from the list it is handed, and falls back to the newest finding's bot when that list is empty — read at `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` § `select_stale_bot_for_trigger`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: review_completeness.py select_stale_bot_for_trigger returns one str: newest_finding_kind_bot or '' when stale_bots is empty, the newest kind if it is in stale_bots, else sorted(stale_bots)[0]
- OBSERVED: trigger B is skipped entirely when `re_review_on_loopback` is `false` (the default), and the step-done guard's remedy text for `participated_stale` names "the `re_review_on_loopback` path above" — read at `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` § trigger B and § "Step-done participation guard (D3)"
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: automatic-review/SKILL.md: re_review_on_loopback default false and 'When re_review_on_loopback == false, skip this entire section'; D3 guard remedy names '(the re_review_on_loopback path above)' for participated_stale
- OBSERVED: the producer already computes the stale set independently of stored findings and returns it as `stale_participation_bots[]` — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` § `cmd_fetch_findings` (the `stale_participation` dictionary in the participation loop)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: github_pr.py cmd_fetch_findings: `stale_participation` dict filled in the participation loop from raw_comments and the currency ledger (not stored findings), returned as stale_participation_bots[] minus participated
- OBSERVED: `bot_claimed_sha_matches_head` and `carry_currency_verdict_to_check_state` are referenced only by their own definitions and by `test/plan-marshall/automatic-review/test_review_currency_holes_regression.py`; every caller of `_derive_overall_status` omits `currency_current` — searched across `marketplace/`, `test/`, `.claude/` and `.github/`; call sites read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` and `_github_ci.py`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: search: both names occur only in _github_checks.py, _github_pr.py (def) and test_review_currency_holes_regression.py; currency_current only in _github_checks.py + that test; .claude/.github not searchable here
- OBSERVED: the currency test runs only for bots with `participation_requires_update: true`; for any other bot the loop credits on the first admissible comment and skips the rest — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` § `cmd_fetch_findings` (`if _bot_kind in participated and not _requires_update: continue`, and the `_requires_update and not _reviewed_at_merge_candidate(...)` guard)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: github_pr.py cmd_fetch_findings: `if _bot_kind in participated and not _requires_update: continue` and `if _requires_update and not _reviewed_at_merge_candidate(...)` are both present in the participation loop
- OBSERVED: of the three registered bots only Sourcery declares `participation_requires_update: false`; CodeRabbit and the in-house reviewer declare `true`. An earlier spec counted CodeRabbit on the untested side; that is no longer so — read at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md`, `coderabbit.md` and `cuioss-review-bot.md` § "Registry data block"
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: Registry blocks (3 standards docs): sourcery.md participation_requires_update: false; coderabbit.md and cuioss-review-bot.md both declare participation_requires_update: true
- OBSERVED: the contract records the untested path as an accepted gap and names what reopens it: a required bot of this kind "observed satisfying the quorum on a merge candidate it demonstrably did not review" — read at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md` § "The currency-blind path for append-per-review bots — an accepted, bounded gap"
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: bot-participation-contract.md currency-blind-path section, 'When it is revisited': the quoted 'observed satisfying the quorum on a merge candidate it demonstrably did not review' is present, gap stated as accepted
- OBSERVED: the comment fetch used by `fetch_findings` builds `review_body` records without the review's commit, while the separate reviews fetch returns `commit_sha` from the REST `commit_id` — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` § `fetch_pr_comments_data` and `_github_pr.py` § `fetch_pr_reviews_with_commits`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: github_ops.py fetch_pr_comments_data review_body record has kind,id,author,body,path,line,resolved,created_at,updated_at,thread_id and no commit; _github_pr.py fetch_pr_reviews_with_commits sets commit_sha from commit_id
- OBSERVED: every stored finding is stamped with the PR head read at fetch time (`reviewed_commit_sha = _github.fetch_pr_head_sha(pr_number)`), not with the commit the comment reviewed — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` § `cmd_fetch_findings`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: github_pr.py cmd_fetch_findings: `reviewed_commit_sha = _github.fetch_pr_head_sha(pr_number)` once per fetch, passed to every add_finding(... reviewed_commit_sha=reviewed_commit_sha or None ...)
- OBSERVED: triage resolves a FIX finding as `fixed` at the moment it allocates the fix task, `fixed` is one of the resolutions `post_responses` transmits, and a thread-bearing finding gets a reply and then a resolve-thread call — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` § 3c FIX, `github_pr.py` § `_RESPONDABLE_RESOLUTIONS` and § `cmd_post_responses`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: triage.md 3c FIX resolves `--resolution fixed` right after commit-add; github_pr.py _RESPONDABLE_RESOLUTIONS contains 'fixed'; cmd_post_responses runs thread-reply then resolve-thread for thread-bearing findings
- OBSERVED: the respond loop runs as Step 8 of the same dispatch that triaged, before the loop-back that executes and commits the fix — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md` § "Step 7: Loop-back signalling" and § "Step 8: Respond loop"
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: verification-feedback.md: Step 7 only signals loop_back_needed (the caller re-fires), and Step 8 'Respond loop' runs post_responses once after triage settles in the same workflow, before any re-entered execute
- OBSERVED: the reply text triage prescribes is "Will be addressed by TASK-{N}; see follow-up commit on this branch", which is future tense; the wording "Fixed in a follow-up commit" came from a dispatch that fixed inline against the documented FIX contract. The thread is resolved early on both paths — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` § 3c and lesson `2026-10-07-07-008`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: triage.md 3c: --detail "Will be addressed by TASK-{N}; see follow-up commit on this branch" and FIX must STOP, never fix inline; cmd_post_responses resolves the thread. Lesson 2026-10-07-07-008 not_found
- OBSERVED: `_match_review` has no author gate by design ("the SHA match already establishes provenance"), so a wait for one bot's review is satisfied by any author's review of that commit submitted after the trigger — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` § `_ReReviewStrategy._match_review`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: github_re_review.py _ReReviewStrategy._match_review docstring: 'There is deliberately NO author gate on this path - the SHA match already establishes provenance'; the loop gates only on commit_sha, submitted_at, refusal
- HYPOTHESIS: a bot's reply inside an old review thread, posted after a fix commit, is credited as a fresh review: it is an `inline` comment, a declared evidence shape for CodeRabbit, has no ledger row and does not predate the commit, so the first-observation arm credits it — confirm/refute at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` § `_reviewed_at_merge_candidate` and § `_is_participation_evidence` with a fixture (verify-at-outline)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: github_ops.fetch_pr_comments_data emits every thread comment as kind inline; coderabbit declares inline ungated; github_pr._reviewed_at_merge_candidate with no ledger row credits unless the comment predates the commit
- HYPOTHESIS: a finding record has no field for the commit that fixed it, so deliverable 4 adds one and a writer for it — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` § `resolve` and the `responded` marker (verify-at-outline)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: manage-findings _findings_core.resolve_finding(plan_id, hash_id, resolution, detail) writes only resolution, resolution_detail, responded, responded_at; search for fix-commit field names finds none in source
- HYPOTHESIS: Sourcery is a required bot in at least one consumer repository, so deliverable 3 changes a merge verdict outside this repository; here it is optional (`.plan/marshal.json` lists `required_bots: cuioss-review-bot,coderabbit`) — confirm/refute by reading `.plan/marshal.json` in each consumer checkout under `/Users/oliver/git/` (verify-at-outline)
- HYPOTHESIS: the in-house reviewer's comment names its reviewed commit as a permalink holding the full 40-character id, so `bot_claimed_sha_matches_head` can read it as written — confirm/refute at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md` § "Participation evidence" and one live comment (verify-at-outline)
- Verify-first clause: PLAN-LB-18 edits the same trigger-B section and `github_re_review.py`. Read what it shipped first: if acknowledgment comments are now excluded from the answer path, deliverable 1's per-bot loop must use the same return fields.
- Verify-first clause: deliverable 3 changes when a bot counts toward the quorum. Before implementing, publish the list of bots it affects (derived from the registry) and the consumer repositories that require one of them, and get the operator's go-ahead. Without it, ship deliverable 3 as disclosure only — a field in the `fetch_findings` return naming each credited bot whose evidence predates the merge commit — and leave the verdict unchanged.
- Verify-first clause: deliverable 4 must not strand a reply. Enumerate every path that ends a plan after a `fixed` disposition without a fix commit (fix task dropped, plan abandoned, finding re-resolved) and state what the reviewer sees on each.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — § "Completion-aware poll" only (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — `cmd_bot_completion` and its argparse entry (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md` — `bot_completion` canonical invocation (D3)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr_bot_completion.py` — bounded-wait tests (D3)
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

- Depends on: none outside this plan. Inside it the order is fixed: the PLAN-LB-05 D3 deliverable first (it settles how a wait is expressed in the step document), then the PLAN-LB-18 deliverables, then the PLAN-LB-19 deliverables. The "Depends on" lines in the carried notes below are satisfied by that order.
- The no-`sleep` document assertion for the completion poll goes into a test module of this plan's own. The shared-name module the source spec proposed, `test_no_standalone_sleep_in_wait_docs.py`, belongs to PLAN-LB-25.
- Overlaps with: PLAN-LB-22, PLAN-LB-25 and PLAN-LB-27 on `phase-6-finalize/SKILL.md` (this plan edits items 7a and 7c only); PLAN-LB-25 on `manage-locks/scripts/merge_lock.py` and `manage-locks/SKILL.md` (that plan adds the admission wait, this one the rate-window wait — whichever lands second reuses the first one's mechanism); PLAN-LB-26 on `plan-marshall/workflow/triage.md` and `verification-feedback.md`. Sequence against those four.
- May run together with: PLAN-LB-23 and PLAN-LB-28, and with PLAN-LB-14, PLAN-LB-29, PLAN-LB-30 and PLAN-LB-31.

### Carried sequencing notes

Copied from the source specs. They use the plan ids from before the regrouping; resolve each through
the id map below. Where a carried "Depends on" or "Overlaps with" line disagrees with the bullets above,
the bullets above are current.

From PLAN-LB-05:

- Overlaps with: PLAN-LB-18 (`automatic-review/SKILL.md`, `manage-locks/SKILL.md`, `merge_lock.py`). Scope boundary: the CodeRabbit rate-window wait — the up-to-an-hour quota wait in `automatic-review/SKILL.md` § "Rate-limit refusal recovery", its Branch 3 poll, the `poll-delay` jitter sleep and the `rate-window` verbs — belongs to PLAN-LB-18. This plan owns the short pacing sleeps (admission, landing, completion poll) and the timeout classification, and must not edit the recovery section. Sequence the two; do not run them together.
- Overlaps with: PLAN-LB-09 (`branch-cleanup.md`, pre-merge check), PLAN-LB-10 (`ci_verify.py`), PLAN-LB-06 (`execution.md`), PLAN-LB-12 (`script-shared/scripts/build/*`), PLAN-LB-19 (`github_pr.py`), PLAN-LB-02 and PLAN-LB-11 (`phase-6-finalize/SKILL.md`). Each touches a different section; sequence rather than pair.
- Adjacent to: the lesson's third proposal, a pre-merge barrier that refuses a merge while a required bot is still in progress for the candidate commit. That is review-gate currency (PLAN-LB-19) and is left out on purpose; deliverable 3 only makes the poll runnable and its outcome visible.

From PLAN-LB-18:

- Depends on: PLAN-LB-05 (unrunnable waits). It decides how a wait is expressed in a step document and owns the short `sleep 30` completion poll in the same skill file. Land it first and reuse its mechanism for the rate-window wait.
- Overlaps with: PLAN-LB-05 on `automatic-review/SKILL.md`, `manage-locks/SKILL.md` and `await-long-running.md`; PLAN-LB-19 on `automatic-review/SKILL.md` (trigger B), `github_re_review.py` and `github_pr.py`. Run the three one after another, never together. PLAN-LB-10 (`manage-status` step records) is adjacent: the stale-record facet of PLAN-24 D1 — `assert-step-recorded` reading an earlier attempt's record on retry — belongs there and is not repeated here.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup-rereview.md` (trigger A). It reads the same `re-review` return fields and gets the acknowledgment fix for free; its prose is not edited unless a field it names is renamed.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md` and `cuioss-review-bot.md`. The new registry fields default to empty for both; no pattern is added for either bot without an observed notice.
- Left out on purpose: turning the enumerative refusal arm on (it needs a measured threshold from a comment corpus); recognising the "Action not completed" wrapper by shape for bots other than CodeRabbit; the rate window as a per-attempt interval with a registry default (PLAN-PR-043 § D6 limbs beyond the hand-back); scoping `rate-window check` to its `--pr-number` (PLAN-PR-043 § D7); close-and-reopen re-stamping the `create-pr` record (PLAN-24 D4); the false-positive metric reading only the resolution enum (PLAN-24 D3, second half).
- Operator decision needed: none to start. If the live check of `@coderabbitai full review` shows it spends quota like any other trigger, the plan reports that and asks before making it automatic.

From PLAN-LB-19:

- Depends on: PLAN-LB-18 (CodeRabbit quota recovery). It owns refusal and acknowledgment recognition in the files this plan edits; classifying staleness on top of an answer path that still reads an acknowledgment as a decline would re-trigger bots for the wrong reason.
- Overlaps with: PLAN-LB-18 on `automatic-review/SKILL.md`, `github_re_review.py`, `github_pr.py` and `_github_pr.py`; PLAN-LB-05 on `automatic-review/SKILL.md` (poll pacing); PLAN-LB-06 on `plan-marshall/workflow/triage.md` (fix-task creation); PLAN-LB-08 on `manage-findings/scripts/_findings_core.py`; PLAN-LB-09 on the pre-merge check in `branch-cleanup.md`, which this plan reads and does not edit. Sequence after each that is in flight.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup-rereview.md` (trigger A, after the pre-merge rebase). It triggers every participating bot already and is not changed.
- Adjacent to: the seven `ext-triage-*/standards/pr-comment-disposition.md` files, which describe FIX as "thread reply linking commit". They already state the intended outcome and are not edited.
- Left out on purpose: (1) storing the commit a review covered separately from the head at which it was fetched, so a re-fetch stops re-stamping old findings (PLAN-PR-053 § D2) — it changes the findings schema and every reader of `reviewed_commit_sha`; (2) refusing to credit a bot's reply inside an old thread as a fresh review (PLAN-PR-070 D2, fourth class) — carried above as a hypothesis to confirm, not fixed here; (3) an author gate on the review arm of the re-review wait, so one bot's wait cannot be satisfied by another author's review (PLAN-PR-070 D6); (4) the in-house reviewer's first clean review, which has no commit link to verify against (lesson `2026-09-19-21-001`).
- Operator decision needed: deliverable 3 — whether a bot that posts per review may lose its credit when its review predates the merge commit, in every repository that requires such a bot. Deliverable 2 — wire or delete; the plan may decide and report.

### Id map

| Id before the regrouping | Now |
|---|---|
| PLAN-LB-01 | PLAN-LB-23 (all deliverables) |
| PLAN-LB-02 | PLAN-LB-22 (all deliverables) |
| PLAN-LB-03 | PLAN-LB-28 (all deliverables) |
| PLAN-LB-04 | PLAN-LB-25 (all deliverables) |
| PLAN-LB-05 | D1 and D2 to PLAN-LB-25; D3 to PLAN-LB-24; D4 to PLAN-LB-26; D5 to PLAN-LB-22 |
| PLAN-LB-06 | PLAN-LB-26 (all deliverables) |
| PLAN-LB-07 | PLAN-LB-27 (all deliverables) |
| PLAN-LB-08 | PLAN-LB-26 (all deliverables) |
| PLAN-LB-09 | PLAN-LB-25 (all deliverables) |
| PLAN-LB-10 | PLAN-LB-22 (all deliverables) |
| PLAN-LB-11 | PLAN-LB-27 (all deliverables) |
| PLAN-LB-12 | PLAN-LB-23 (all deliverables) |
| PLAN-LB-13 | PLAN-LB-28 (all deliverables) |
| PLAN-LB-14 | unchanged, still PLAN-LB-14 |
| PLAN-LB-15 | PLAN-LB-29 (all deliverables) |
| PLAN-LB-16 | PLAN-LB-30 (all deliverables) |
| PLAN-LB-17 | PLAN-LB-29 (all deliverables) |
| PLAN-LB-18 | PLAN-LB-24 (all deliverables) |
| PLAN-LB-19 | PLAN-LB-24 (all deliverables) |
| PLAN-LB-20 | D1 to D3 to PLAN-LB-30; D4 and D5 to PLAN-LB-31 |
| PLAN-LB-21 | PLAN-LB-31 (all deliverables) |

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-24-review-step.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
