envelope_version=1
sender_type=plan
sender_id=lessons-corpus-is-written-and-never-read
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T18:43:53Z

component=plan-marshall:workflow-integration-github
category=bug
created=2026-07-28

# `responded_bots` lists a rate-limited reviewer that never reviewed (recurrence of #1026)

On PR #1039, `sourcery` was rate-limited (its weekly 500000 diff-char
cap) and did NOT review the pull request. `github_pr fetch_findings`
nonetheless still listed `sourcery` in `responded_bots`. A caller trusting
`responded_bots` at face value over-counts the number of reviewers that
actually examined the diff.

This is the SAME defect class previously recorded against #1026: "a
detected refusal was still reported as a clean review." The prior
occurrence and this one both stem from the same root cause —
`responded_bots` is populated from the bot's *check-run completion*
signal (the bot ran to completion and posted SOME status, even a
refusal/rate-limit notice), not from evidence that the bot actually
examined the diff content. A completion signal and a genuine review are
conflated into one field.

## Solution

`fetch_findings` should distinguish "bot posted a completion status" from
"bot posted actual review content" — e.g. by checking whether the bot's
completion payload carries a rate-limit / refusal marker (as it did here)
before adding the bot to `responded_bots`. Absent that distinction, every
downstream consumer of `responded_bots` (review-retrospective comparisons,
reviewer-count reporting) must re-derive true participation by cross-
checking `ci pr comments` — the one source of evidence this repo's own
memory has already flagged as authoritative — rather than trusting the
field.

## Impact

Every PR review-retrospective or reviewer-count report that reads
`responded_bots` directly (without cross-checking `ci pr comments`)
over-counts participating reviewers whenever a configured bot is
rate-limited, quota-exhausted, or otherwise refuses without commenting.
This plan's own `finalize-step-review-retrospective` step caught the
mismatch manually ("2 reviewers compared... sourcery no-participation
noted") — the fix should make that catch automatic instead of relying on
a human/LLM re-check each time.
