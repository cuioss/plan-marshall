envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T17:03:05Z

component=plan-marshall:workflow-integration-github
category=bug

# Review coverage on #1061 was thin — a green finalize is not three-way confirmation

Recording the actual review coverage of PR #1061, because the finalize signal does not distinguish it from a well-reviewed PR.

Three review bots are configured. **One** produced a substantive automated review:

| Bot | Outcome |
|-----|---------|
| `pr-agent` (required) | Participated. One "no major issues detected" guide. |
| `sourcery` | **Explicitly refused** — hard quota exhausted. |
| `coderabbit` | Check **completed**, but produced **no comment** creditable as review evidence. |

So: one substantive automated review out of three configured bots, and the one that landed found nothing. The finalize gate went green. Nothing in the green says which of those three columns it came from.

The `coderabbit` row is the sharp one — a **completed check with no review comment**. That is precisely the "check states lie in both directions" failure: a green check is not evidence of participation, and only `ci pr comments --pr-number N` is. It is also the second axis of the standing rule: `ci pr comments` is *necessary but not sufficient* (a comment *from* a bot is not a review *by* it) — and here the converse bit, a completed check *without* a comment.

## Solution

- **Do not read a green finalize as three-way confirmation.** Record per-bot participation explicitly in the landing, naming refusals and silent completions.
- Distinguish three states per configured reviewer and surface all three: **reviewed** (substantive comment), **refused** (explicit decline — quota, size, config), **silent** (check completed, no comment credited). Only the first is review coverage.
- When coverage is thin, the merge decision should know it. Thin coverage does not block, but it must not be invisible.
- **Post-merge PR revisit is mandatory** for a thinly-reviewed landing: the merge routinely outruns the review (58s on #1026, 2m42s on #1036), so a late review is a recurrence to be scanned for, not an incident to be surprised by.

## Impact

Reinforces the standing review-bot rules with a fresh instance carrying a new sub-case: a bot whose **check completed but produced no review** — a silent-zero that reads identically to a clean review in every downstream signal. Also a quota-exhaustion data point for `sourcery`, which suggests the third-reviewer slot is not reliably available and should not be counted on for coverage.
