envelope_version=1
sender_type=plan
sender_id=wrong-store-guard-refuses-project-local-lessons
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T11:56:56Z

component=plan-marshall:tools-integration-ci
category=anti-pattern
created=2026-07-29

# Review-bot green-check-lie recurrence: a review-fix commit landed with zero bot coverage

The review-fix commit `28a1e041d` on PR #1050 was reviewed by no bot. Sourcery hit `hard_quota`, CodeRabbit's review is timestamped against the FIRST commit only (never re-ran against the fix), and pr-agent has no `synchronize` trigger so its check never re-fired on the new commit. An explicit re-review was requested and the plan awaited 319s — no new review was submitted before finalize proceeded (operator explicitly accepted the gap).

## Impact

This is the same green-check-lie class already tracked in the `truthful-signals` epic (`ci pr comments` is necessary but not sufficient evidence of participation) — here it recurs specifically on a REVIEW-FIX commit, which is exactly the commit most likely to introduce a NEW defect (see the vacuous-guard candidate-lesson from this same plan) and least likely to get bot eyes, because the tooling's re-review triggers are keyed to the ORIGINAL push, not to fix commits layered on top of an already-reviewed head. A `ci verify` or finalize-time check that a fix-commit's SHA has at least one review timestamp newer than its own commit time would catch this mechanically instead of relying on an awaited-but-unanswered re-review request.
