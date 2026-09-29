envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:44:01Z

# automatic-review: a CodeRabbit "Review triggered" acknowledgment is matched as a decline

**Observed (plan-12-tool-triage, automatic-review re-fire at dd28b5002, 2026-09-29):** after the rate window elapsed, `github_re_review re-review` posted one `@coderabbitai review` (11:41:47Z) and returned in 105 s with `matched: true, matched_signal: issue_comment, head_sha_verified: false`. The matched comment (11:43:00Z) was CodeRabbit's "Action performed — Review triggered." — an acknowledgment, not a review and not a refusal. At the same moment `github_pr bot_completion --bot-kind coderabbit` reported `in_progress: true`. The workflow routes `matched && !head_sha_verified` to `declined`, so the step returned `escalate_ask{reason: re_review_timeout, outcome: declined, declined_bots: coderabbit}` while the review was actually running.

**The defect:** the fresh-review matcher accepts any post-trigger bot issue comment as the response signal and then reads "not head-verified" as a decline. A trigger acknowledgment is neither. The resulting escalation offers "Merge anyway — proceed unreviewed" against a review that is in progress, and a plain re-dispatch re-enters the loop-back re-review path from scratch (stored findings still carry the old reviewed-at SHA), posts another trigger, and is expected to match "Already reviewed the last commit" as another decline — a loop.

**Related:** the loop-back path fires one selected bot per pass (`trigger-bot` chose coderabbit), so the second stale required bot (cuioss-review-bot) is never re-triggered while the first keeps escalating.

**Suggested fix:** classify acknowledgment comments ("Review triggered", "Actions performed") as `acknowledged` and continue into the completion poll (check-run / bot_completion) instead of the decline branch; treat `in_progress: true` from `bot_completion` as authoritative over an unverified issue-comment match.
