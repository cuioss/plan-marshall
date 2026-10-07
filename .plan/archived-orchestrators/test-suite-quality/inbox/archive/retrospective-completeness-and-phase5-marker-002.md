envelope_version=1
sender_type=plan
sender_id=retrospective-completeness-and-phase5-marker
epic=test-suite-quality
kind=candidate-lesson
created=2026-07-28T16:24:45Z

component=plan-marshall:automatic-review
category=anti-pattern
proposed_bundle=plan-marshall
origin_plan=retrospective-completeness-and-phase5-marker
origin_pr=1036

# A review bot's "Action performed / Review finished" is a success string, not evidence a review happened

On PR #1036 CodeRabbit answered an explicit `@coderabbitai review` request with a green
success string **while simultaneously admitting, in a comment it updated four seconds
earlier, that it could not review at all**. It posted zero review content.

## Evidence (verbatim, from `ci pr comments --pr-number 1036`)

| Time (UTC) | Author | What |
|------------|--------|------|
| 14:41:05 | `sourcery-ai` | "you have reached your weekly rate limit of 500000 diff characters" |
| 14:41:14 | `coderabbitai` | "⚠ Review limit reached … we couldn't start this review." Enumerates the 10 files it *would* have reviewed. |
| 14:42:07 | `cuioss-review-bot` (pr-agent) | Content-free "PR Reviewer Guide" table |
| 15:43:59 | operator | `@coderabbitai review` |
| **15:44:05** | `coderabbitai` | **"✅ Action performed — Review finished."** |
| **15:44:11** | `coderabbitai` | the *rate-limit comment above* is **updated**, refreshing "Next review available in: **46 minutes**" |

The success string at 15:44:05 and the still-rate-limited notice refreshed at 15:44:11 are
the same bot, six seconds apart, on the same PR. The "Review finished" reply carries its own
disclaimer in small print — "CodeRabbit is an incremental review system and does not
re-review already reviewed commits" — but the commits had **never** been reviewed, so the
disclaimer describes a no-op the reader is invited to interpret as completion.

## Why this is the epic's own archetype, turned on the tooling

`test-suite-quality` exists because *a confident signal hid a caveat*. This is that theme
appearing **inside the review tooling that is supposed to catch it**:

- A **string that names the goal** ("Review finished") was emitted by a path that did not
  reach the goal. Structurally identical to the vacuous-guard archetype this epic has now
  hit five times: the code says the thing happened; the predicate that would make it happen
  never fired.
- **Second burn in the same epic.** The first was #1026, where a *detected* bot refusal was
  still reported as a clean review. The recurrence means the standing rule
  ("only `ci pr comments` is evidence of participation") is necessary but **not sufficient**
  — here `ci pr comments` *was* run and returned six comments; the defect is that a comment
  from the bot was read as a review by the bot.

## Corrective rule

**Never accept a review bot's own status prose as the completion oracle. Derive
participation from review CONTENT, not from a bot's self-report.**

Concretely, for `plan-marshall:automatic-review` and
`project:finalize-step-review-retrospective`:

1. A reviewer counts as *having reviewed* only when it emitted at least one comment that is
   **not** a rate-limit notice, a command acknowledgement, or a content-free summary table.
   Bot acknowledgement bodies (`<!-- This is an auto-generated reply by CodeRabbit -->`,
   `✅ Action performed`, `Review limit reached`, sourcery's rate-limit body, pr-agent's
   bare "PR Reviewer Guide" table) are **meta**, and meta ≠ participation.
2. When a bot posts a rate-limit / refusal notice on a PR, that refusal must be recorded as
   a **first-class non-participation fact for that PR head**, and must NOT be cancelled by a
   later success string from the same bot unless real review content accompanies it.
3. `review-retrospective`'s "N of M reviewers reviewed" headline must be computed from (1).
   On #1036 it reported "1 of 3"; by (1) the truthful answer is **0 of 3**.

## Impact

Every PR that finalizes while a review bot is rate-limited. The failure is silent by
construction: finalize goes green, the retrospective reports a reviewer count > 0, and the
diff was never read by anything. Rate limits are hit routinely on this org (both CodeRabbit
and Sourcery refused within nine seconds of each other on this PR), so this is the common
case, not the edge case.
