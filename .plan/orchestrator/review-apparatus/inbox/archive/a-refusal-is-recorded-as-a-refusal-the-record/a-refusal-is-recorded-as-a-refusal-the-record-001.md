envelope_version=1
sender_type=plan
sender_id=a-refusal-is-recorded-as-a-refusal-the-record
epic=review-apparatus
kind=finding
created=2026-08-30T19:57:34Z

# Trigger B cannot re-trigger a stale required bot, and CodeRabbit's refusal shapes are under-registered

Observed live on PR #1368 during PLAN-PR-025A's finalize, at head `5892ee9a1`.
Both items are `review-apparatus` surface. Neither blocked the landing; both are
structural and will recur on any plan whose head advances after the first review.

## 1. Trigger B can never re-trigger a stale required bot

`pr-agent` is this project's only **required** bot. After the branch was rebased and
force-pushed, its Guide comment stayed anchored to a superseded commit, so the
participation guard classified it `participated_stale`. The declared remedy for
`participated_stale` is a re-review trigger, not a wait.

But trigger B selects exactly **one** bot, and it selects it from *the newest
bot-authored finding*. On this PR that is CodeRabbit, and it will remain CodeRabbit
on every re-entry, because CodeRabbit comments most recently. So:

- `pr-agent` is the bot that gates the merge,
- `pr-agent` is the bot whose remedy is a re-trigger,
- and `pr-agent` is the one bot trigger B structurally cannot select.

The loop does not converge. Each finalize re-entry re-runs the identical pass and
re-reports `participation_complete: false` with the same `unproven_bots`. The
observable that says "re-trigger me" and the mechanism that re-triggers are wired to
different selectors.

Worth noting the selector is also **stale by construction**: trigger B picks its bot
from findings filed *before* the round's own FIND, so on this run it could not see
that CodeRabbit had already auto-reviewed the new head. It therefore posted a trigger
that CodeRabbit declined as redundant, and burned that bot's hourly quota to do it
(`0 remain` afterwards).

Candidate remedies, in rough order of directness — all unvalidated:

- select the trigger-B bot from the **unproven/gating** set rather than from comment
  recency, so the bot that gates is the bot that gets triggered;
- allow trigger B to trigger more than one bot when more than one is unproven;
- re-read the store *after* the round's FIND so the selector sees the current state.

## 2. CodeRabbit's command-reply refusals are under-registered, and widening the
   literal is the WRONG fix

PLAN-PR-025A registered `Review rate limited` after observing that shape reach the
producer as an actionable comment and reach `github_re_review` as `matched: true`
(a refusal credited as a completion signal). That fix is confirmed working for that
shape.

This run produced **two further bodies** under the same
`<details><summary>⚠️ Action not completed</summary>` wrapper, neither registered:

- *"Already reviewed the last commit. Use `@coderabbitai full review` to rerun…"*
  → stored as an actionable `pr-comment` finding.
- *"Review skipped / No new commits to review since the last review"*
  → `matched: true`, `matched_signal: issue_comment`, `refusal_detected: false`.

Both are the two wrong outcomes the original fix exists to prevent, recurring on
unregistered siblings of the registered shape.

**The obvious fix is wrong.** Registering the wrapper marker `Action not completed`
would catch all three — but `rate_limit_class` is declared **per bot**, and CodeRabbit
declares `awaitable_window`. A redundancy decline ("already reviewed this commit") is
not a window that reopens; classifying it `awaitable_window` would arm a wait that
can never succeed, which is precisely the non-option the refusal-cause work exists to
abolish. The narrow literal was the right call at the time and remains so.

What is actually missing is a **second decline class**: a non-awaitable,
non-structural "the bot declined because there is nothing to review" outcome,
distinct from both `size` (shrink the diff) and `quota` (wait for the window). The
stable observable across all three bodies is the `⚠️ Action not completed` summary
marker and/or the `CodeRabbit review command invocation:` HTML comment — so detection
is easy; it is the **classification** that needs designing.

Mitigating context for triage: on this run the decline was truthful — CodeRabbit had
genuinely auto-reviewed the head, and its real review was filed separately. So this
is a misclassification, not lost review coverage.

## Provenance

- PR: https://github.com/cuioss/plan-marshall/pull/1368
- Head observed: `5892ee9a1f9697c8aeeb21fc8bb3861ff8172269`
- Confirmed working in the same run (recorded so it is not re-litigated):
  the `refusal_pattern_drift` narrowing. Sourcery refused again by the same
  registry-only path and produced **no** drift record, where the pre-fix predicate
  had falsely emitted one. A matched negative control against live data.
