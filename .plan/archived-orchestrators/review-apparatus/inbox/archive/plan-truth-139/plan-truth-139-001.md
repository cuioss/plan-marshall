envelope_version=1
sender_type=plan
sender_id=plan-truth-139
epic=review-apparatus
kind=finding
created=2026-09-13T13:26:27Z

# cuioss-review-bot's review WAS published; the participation detector did not see it

kind: finding
source_plan: plan-truth-139
evidence_pr: https://github.com/cuioss/plan-marshall/pull/1479
observed: 2026-09-13, first-party across six FIND rounds on one PR

## The claim, corrected by the operator

Across every review round of PR #1479 the `automatic-review` FIND reported
`cuioss-review-bot` as `participated_but_empty` and then `participated_stale`,
and on that basis the participation quorum was reported UNSATISFIABLE and the
merge was blocked. **The operator's reading is that the review was there and the
detection logic is what failed.** This message records the defect against the
detector, not against the bot.

## What the bot actually published

Two comments on #1479, both authored by `cuioss-review-bot`:

- `2026-09-12T21:56:02Z` — "## PR Reviewer Guide 🔍" with a table reporting
  `PR contains tests`, `No security concerns identified`, `No major issues
  detected`.
- `2026-09-12T21:57:03Z` — "## PR Code Suggestions ✨ — No code suggestions
  found for the PR."

Neither was ever edited (`updated_at == created_at` on both).

## How the detector classified it, and why that is the defect

1. **Both publications were bucketed as contentless noise**, so the run's
   `count_stored: 0` decomposed as "noise + refusals" and the bot resolved to
   `participated_but_empty`. A reviewer that examined the diff and reported
   *nothing to report* is a REVIEW WITH NO FINDINGS. Treating its verdict as
   an absence of participation is the confident-signal-hides-a-caveat shape:
   the strongest possible clean result is read as no result.
2. **Once the head advanced it became `participated_stale`**, because the
   currency test anchors on the merge-candidate commit and the bot has no
   push trigger and no completion check (`bot_completion` → `no_check_name`).
   So after any loop-back it can never be proven current: the only remedy the
   registry names for `participated_stale` is a re-trigger, and a delivered
   `/review` at `2026-09-13T08:56:30Z` produced nothing in 617s of polling
   (19 polls, `refusal_detected: false`). A required bot whose only remedy
   does not move it makes the quorum structurally unsatisfiable rather than
   merely unmet.
3. **The state pair is therefore non-actionable by construction.** Neither
   `participated_but_empty` nor `participated_stale` can be cleared for this
   bot by any action available to the step, so the gate it feeds can only ever
   block or be overridden — which is what happened here.

## Two adjacent detector defects observed on the same PR

Both are already filed as plan-local findings and are named here so the epic
has them in one place:

- `af8660` — the currency test's FIRST-OBSERVATION arm credited `coderabbit`
  as `participated` from a comment that demonstrably PREDATED the reviewed
  range (newest activity 01:25:47Z against an earliest range commit of
  01:45:42Z). The same run simultaneously placed it in `refused_bots[]`, and
  participation won. A false green at the review gate, the mirror of the
  false red this message is about.
- `867ba4` — no `escalate_ask` reason covers "window claimed, wait delegated
  to the orchestrator", so a leaf that hands the >=90min quota wait upward has
  to borrow `re_review_timeout` and carry the refusal fields beside it.

## Why the `participated` verdict for coderabbit was coincidentally right

At the final head CodeRabbit's fresh review arrived as an IN-PLACE EDIT of its
existing summary comment (`updated_at 2026-09-13T12:55:18Z`), which
`movement_matched_bots[]` cannot see because coderabbit declares
`participation_requires_update: false`. The credit was instead drawn from older
inline comments. The verdict was correct, but not derived from the artifact that
proved it — and a genuinely stale coderabbit carrying any old inline comment
would render `participated` identically. Only reading the body's own stated
range (`1e2fddb7b..0e8ac4423`, `coveredCommitId`, `kind: reviewed`) discriminated.

## Suggested direction (not a prescription)

The detector needs to distinguish three things it currently conflates: a
reviewer that did not run, a reviewer that ran and reported nothing, and a
reviewer whose report is older than the head. The second is a pass. For a bot
with neither a completion check nor a push trigger, "current" may simply not be
establishable, in which case the honest move is to say so rather than to
report non-participation.
