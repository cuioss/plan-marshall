envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:16:06Z

component=plan-marshall:automatic-review
category=bug
bundle=plan-marshall

# Pre-merge review barrier fed a DEDUPED participation set to the predicate and falsely reported the required bot absent

## What happened

At the pre-merge barrier on #1057 the re-fetch returned `participated_bots=[]`, because its dedup skipped pr-agent's already-stored comment (`count_skipped_duplicate=1`). `review_completeness` consumed that empty set and reported the **required** bot pr-agent as absent — a merge block.

The block was wrong. Re-deriving participation from the findings store showed the evidence was present and current: hash `0b335e`, `bot_kind=pr-agent`, `kind=issue_comment`, `reviewed_commit_sha=0b9b248` — identical to HEAD. Re-running with `--participated-bots pr-agent:issue_comment` returned `participation_complete=true` and the barrier cleared: 0 pending pr-comment findings, required bot participated, optional bots coderabbit/sourcery refused (non-gating).

## Root cause

`branch-cleanup.md` instructs the agent to feed the **output of the deduped `fetch_findings` call** to the participation predicate. But dedup is a *storage* concern — it answers "have I already stored this comment?" — and the predicate asks a *participation* question — "did this bot review this HEAD?". A comment that is skipped as a duplicate is the strongest possible evidence of participation, and the current wiring converts it into evidence of absence.

The polarity is exactly inverted: the more established a bot's participation is, the more likely its comment is deduped, and therefore the more likely the barrier is to declare it absent.

## Why it matters for truthful signals

This is a **false merge block**, which is the failure direction that gets diagnosed and worked around rather than reported — the operator or agent sees a block they know is wrong, overrides it, and moves on. On this run the override was correct and was documented. On the next run the same shape produces either a stalled merge or, worse, a habit of overriding a barrier that will one day be right.

It also sits directly on the epic's standing rule that **`ci pr comments` is necessary but not sufficient** as participation evidence. Here the tooling had the right evidence in the findings store and discarded it at the wrong layer.

## Corrective rule

**Participation must be derived from the findings store, not from the return value of a deduping fetch.** Concretely:

1. `branch-cleanup.md` must stop passing the `fetch_findings` return set to `review_completeness --participated-bots`.
2. The participation set must be queried from stored findings filtered on `reviewed_commit_sha == current HEAD`, so a deduped-but-stored comment counts.
3. `fetch_findings` should surface `count_skipped_duplicate` to its caller as a first-class field precisely so a caller cannot mistake an empty return for an empty world.

**A deduplicating reader's empty return means "nothing NEW", never "nothing".** Any predicate that treats the two as the same is inverted.

## Recurrence signature

Sweep for callers that treat a deduping/filtering call's empty result as an empty domain. The same shape exists anywhere a "new items" query backs an "any items" question.

## Provenance

Discovered at 15:46:27 during branch-cleanup, **after** `lessons-capture` had already closed at 15:41. The decision-log entry claims "Defect filed for the epic" but no such message exists — see the companion candidate-lesson on finalize step ordering. This message is that filing.
