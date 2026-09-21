envelope_version=1
sender_type=plan
sender_id=two-producers-one-marker-field-two-encodings
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T05:11:31Z

# Owed architecture hint — review-bot meta comments are consistently non-actionable

Filed by `default:finalize-step-preference-emitter` at `order: 992`. This step is
`post_run_review: true` and runs after the merge gate, so it does NOT call
`architecture enrich` — writing `.plan/project-architecture/{module}/enriched.json`
post-merge would land tracked source on `main` as an unpushable diff (the `#990`
defect). The hint is named here so the enrichment is scheduled and visible rather
than lost.

## The pattern

One `(module, finding-class, disposition)` tuple cleared the within-plan
`preference_min_recurrence` threshold of 2:

| module | finding-class | disposition | recurrence |
|---|---|---|---|
| `plan-marshall` | `pr-comment` — CodeRabbit bot-action notice / review-summary body | `accepted` | **6** |

The six: `e15cef`, `9ed263` (review-summary bodies reporting "Actionable comments
posted: N"), and `036de6`, `cefd79`, `c8180d`, `7255b6` (bot-action notices —
"Already reviewed" / "No files to review").

Zero findings were `suppressed`. One was `taken_into_account` (`0dfd38`, the
author's own non-goals comment), which is a distinct class at recurrence 1 and
does not clear the threshold.

## The generalization

Every member of this pattern is a **mechanical bot emission carrying no reviewer
judgement about the diff**, and every one was dispositioned `accepted` after a
human-equivalent read confirmed it contained nothing to fix, suppress, or dispute.
The disposition is not a judgement call that varied by case — it was forced by the
content class in all six.

**Owed hint** — `architecture enrich best-practice --module plan-marshall`:

> A review-bot emission whose body is a bot-action notice ("Already reviewed", "No
> files to review", "Action not completed") or a review-summary wrapper ("Actionable
> comments posted: N" plus run configuration and file lists) carries no reviewer
> judgement about the diff. It is consistently dispositioned `accepted` and never
> produces work. The comment-fetch filter should classify this shape as noise at
> FIND time rather than storing it as a pending finding.

## Why this is worth acting on rather than merely recording

The pattern is not cosmetic. Two independent measurements from this same run:

1. The review retrospective measured **7 of 11 stored findings (64%) carrying zero
   code feedback**, with the four bot-action notices accounting for 36% of the
   ledger on their own.
2. One member of this exact class — `7255b6` — **blocked the merge**. It was
   CodeRabbit's auto-reply to the re-review trigger comment `branch-cleanup` itself
   posted, and because `pr-comment` is in the hardcoded ACTIONABLE blocking set, a
   pending bot-action notice failed the Pre-Merge Review-Completeness Barrier. Left
   unfixed it is a livelock: each re-entry re-fires the trigger, draws a new reply
   under a new comment id that dedup cannot catch, and blocks again.

So filtering this shape at FIND time is not noise reduction for its own sake — it
removes a class that can deadlock the merge gate.

## Bound on the claim

The recurrence is **within this single plan**, which is what this step measures by
construction. It is not a cross-plan frequency. The richer corpus-wide evidence
belongs to the meta-only `audit-archived-plan-retrospectives` auditor, and this
hint should be corroborated there before it is treated as a standing rule rather
than a one-plan observation.
