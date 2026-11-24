envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:08Z

component=plan-marshall:automatic-review
category=improvement
title=Bot quota recovery: hour-long rate-window waits for trivial fixes and repeated close-and-reopen
source_lesson=2026-11-18-13-005
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# Bot quota recovery: hour-long rate-window waits for trivial fixes and repeated close-and-reopen

# Candidate lesson: review-bot quota recovery wastes wall-clock and repeats close-and-reopen

- Source signal: automatic-review, plans git-core-import PR 25 (inbox git-core-import-005) and plan-18-leftover-fixes PR 26/27/28 (inbox plan-18-leftover-fixes-014).

## What happened

1. git-core-import, iteration 4 (granted): a one-line Sonar S5778 test fix was committed; the automatic-review re-run then hit the CodeRabbit rate window and the plan waited about 56 minutes (12:35:50Z to 13:32:31Z, bounded by 5400 s) for a review that produced nothing new. The wait held the plan's place in the epic queue.
2. plan-18-leftover-fixes: CodeRabbit refused on its free OSS quota. The recovery selector returned `close_and_reopen` (reason `claim_window_elapsed`) twice, so PR 26 was closed and re-opened as 27, and 27 again as 28. Each re-open discards the comment history, re-runs the CI matrix, forces a `pr_number` re-bind, and cost two `blocked_session_restart` finalize dispatches (247K retryable tokens) plus operator decisions, with no operator ask before the first two.

## Candidate rule

- Skip or downgrade the bot re-review when the delta since the last reviewed commit is trivial (test-only, Sonar-rule-only, below a line threshold), or batch the Sonar fix into the previous round's commit.
- For a bot with `requires_explicit_trigger`, prefer an explicit in-PR trigger as the re-delivery event once the window elapsed; cap close-and-reopen at one per plan without an operator decision and record the chain of replaced PR numbers.
- Surface the remaining bot quota before a loop-back is granted.


## Recurrence in a later plan (git-worktrees-hardening, inbox plan-19-git-worktrees-hardening-010)

- Source signal: automatic-review re-run after the TASK-11 loop-back (work log 22:10:31Z to 22:46:05Z, a lock-waiting window 22:14:43Z to 22:45:40Z).
- The first CodeRabbit review of PR #31 (about 21:43Z) used the only included review of the hour ("Your plan provides up to 1 included review per hour; 0 remain after this review"). The loop-back fix commit 9b4f3b8 was pushed about 25 minutes later and CodeRabbit refused to review it; the run settled it with `accept_review_on_record` after about 31 minutes of waiting.

Same root cause: a fix pushed inside the bot's rate window. Extra rule from this run: decide up front, from the previous review's quota line (or the rate-window claim), whether to wait for the window or accept the review on record for the earlier head with the fixed findings listed, and record the window end so the wait is bounded and visible. The hourly quota is shared across the plans of one epic; staging PRs so that two do not land in the same hour avoids the wait.


## Recurrence in a later plan (plan-21-merge-worktrees-into-core, inbox plan-21-merge-worktrees-into-core-006 and the landing)

- Source signal: plan-retrospective, not lessons-capture. After the Sonar loop-back commit 6b45edb, automatic-review iteration 2 returned `escalate_ask` with `reason: rate_window_await` and claimed a 2100 s CodeRabbit rate window, although the same pass had established that no re-review was owed (`participation_complete: true`, CodeRabbit in `review_complete_bots` for 6f5b7cd, `re_review_on_loopback: false`, `required_stale_bots` empty, nothing re-triggered). The claim was made because the recovery-action consult answered `unmeasured, no_window_observation` and routed to Branch 2. The orchestrator waited from 16:55:20Z to 17:31:06Z (about 35 minutes, more than the 33m23s of idle time `metrics.md` attributes to the closed phases); iteration 3 then returned `accept_review_on_record` (`review_on_record_done`, 0 pending CodeRabbit findings) and posted nothing.

Same root cause: a wait whose review was never requested. Extra rule from this run: before arming a rate-window claim, check whether a re-review is owed at all (`re_review_on_loopback`, `required_stale_bots`, a finished review on record) and, when none is owed, take the accept-review-on-record path directly by passing `--finished-review true` to the first recovery-action consult. Owning component: automatic-review (refusal-recovery branch selection, the consult inputs).


## Recurrence in a later plan (plan-20-leftover-fixes-2 and plan-11-store-anchoring-signed, inbox plan-20-leftover-fixes-2-007, plan-11-store-anchoring-signed-012)

Close-and-reopen churn again, now at two plans. plan-11: PR #65 closed unmerged and replaced by #66 (same head branch) when automatic-review re-opened it so CodeRabbit would review after its quota window; #66 merged. plan-20: refusal recovery armed on PR 67 at 2026-11-23T20:11:10Z (window 2700 s), re-delivered by close-and-reopen as PR 68 at 21:02:01Z (the decision line itself says it "buys back no quota - the limit is account-scoped"), PR 68 drew a fresh refusal (window 3360 s) and was re-delivered as PR 69 at 22:05:07Z. About 1.5 hours of window waits plus about 27 minutes of step time; the history of one change is spread over #67, #68 and #69; later passes (2026-11-23T23:02:35Z, 2026-11-24T06:38:37Z) were accepted without a trigger because a finished review was on record. Rule: on a free-tier account a quota refusal is not cured by close-and-reopen, wait for the window on the same PR or accept a finished review on record before churning PR numbers; this is a framework candidate for the refusal-recovery branch of automatic-review.
