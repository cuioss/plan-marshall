envelope_version=1
sender_type=plan
sender_id=post-merge-review-findings-untriaged-in-main
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T10:01:32Z

# wait-for-comments cannot see an in-place comment update, so a bot that edits its guide reads as never having reviewed

category: bug
component: plan-marshall:workflow-integration-github

## What happened

On PR #1045, pr-agent re-reviewed HEAD `a9b2c4d0c` and recorded it by **updating
its existing PR Reviewer Guide comment in place** — `updated_at 09:10:26Z`, body
text `Review updated until commit a9b2c4d0c94...` — one minute after the
`/review` trigger at `09:09:18Z`.

`ci pr wait-for-comments` counts only **new** comments. Across three waits
totalling ~23 minutes it returned `new_count: 0` every time, and
`review_completeness check` returned `participation_complete: false` with
`unproven_bots: [pr-agent, sourcery]`.

The orchestrator therefore concluded that pr-agent — the plan's only REQUIRED
bot — had never reviewed the merged SHA, recorded a `[WARNING]` to that effect,
and escalated the merge decision to the operator **twice on a false premise**.
Only listing the comments and reading `updated_at` surfaced the truth.

## Two distinct defects

1. **The completion detector counts rows, not evidence.** For a bot whose
   evidence is an in-place edit, participation must be established by comparing
   `updated_at` against the trigger time, or by matching the reviewed-commit SHA
   the bot writes into its own body — never by counting new comments.
2. **No corroborating signal.** pr-agent declares no `completion_check_name`, so
   `bot_completion` returns `no_check_name` and cannot confirm or deny. With the
   comment poll blind and the check-run absent, there was no true signal at all.

## Why it matters

This is a textbook instance of the epic theme: a confident signal
(`new_count: 0`, `participation_complete: false`) asserting the exact opposite of
the truth. It did not merely fail to detect participation — it actively reported
non-participation, which is a stronger and more misleading claim.

The standing rule "only `ci pr comments` is evidence of participation" is
correct but insufficient as stated: it must add that a comment's `updated_at`
and its self-reported reviewed-commit SHA are part of that evidence, not just
its existence.
