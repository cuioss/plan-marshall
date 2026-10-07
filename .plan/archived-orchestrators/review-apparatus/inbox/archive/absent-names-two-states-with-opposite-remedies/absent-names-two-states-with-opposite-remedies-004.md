envelope_version=1
sender_type=plan
sender_id=absent-names-two-states-with-opposite-remedies
epic=review-apparatus
kind=candidate-lesson
created=2026-08-08T20:42:22Z

# Candidate lesson: the barrier passed on a quorum in which no bot reviewed the final two commits

**Source record:** `[VERIFY]` WARNING, `plan-marshall:phase-6-finalize`, work log `2026-08-08T19:53:48Z`, hash `ffaf11`. PR #1118, HEAD `a5749b0d2`.

## The observation, verbatim from the run

> Pre-merge barrier PASSES at HEAD a5749b0d2: 0 pending pr-comment findings, participation_complete=true. The quorum rests on pr-agent=participated_but_empty (a contentless 'no major issues' guide). coderabbit=refused_awaitable (will not re-review already-reviewed commits), sourcery=refused_hard (diff over 150000 chars). Commits 851e5396b and a5749b0d2 carry NO bot review content. Participation proven, review quality NOT.

## Why this is the epic's central finding from this run

The two commits that carry no bot review content are **precisely the commits that implement the review's own fixes**. CodeRabbit found 8 actionable comments including a Major; `851e5396b` is the 9-task response to them and `a5749b0d2` is the 5-task follow-up. Neither was reviewed by anything. The apparatus therefore produced a strong review of the code as it was BEFORE the review, and no review at all of the code as it merged.

Every one of the three bots declined for a different and individually reasonable reason, and none of the three reasons is a bug:

| Bot | State | Reason |
|---|---|---|
| coderabbit | `refused_awaitable` | will not re-review commits it has already reviewed |
| sourcery | `refused_hard` | diff exceeds the 150000-character limit |
| pr-agent | `participated_but_empty` | returned a contentless "no major issues" guide |

`participation_complete` is a **liveness** predicate — did every required bot show up. It is not, and was never, a **coverage** predicate — did every required bot look at what is about to merge. On a normal run those two coincide, which is why the gap is invisible until a run like this one separates them.

## The generalisable shape

A quorum computed over *who responded* certifies participation. It does not certify that any response contained content, nor that any response was about the current HEAD. `participated_but_empty` is by design an accounted-for, never-blocking member — correctly so, since a genuine clean review is indistinguishable from an empty one at the participation layer. But when it is the ONLY member carrying the quorum, "accounted for" has silently become "reviewed", and the barrier reports green on evidence that contains no review.

Note the interaction with this plan's own deliverable: `participated_stale` exists to catch a review that is about a superseded HEAD. It fired earlier in this same run and worked. It did not, and cannot, catch the case where the bot never produced content about ANY HEAD.

## Candidate remedies (none applied — this run only recorded the state)

- Distinguish `participation_complete` from a `review_coverage` signal that asks whether the merging HEAD received at least one content-bearing review, and decide deliberately which one gates a merge.
- Treat "the quorum rests on a single `participated_but_empty`" as a state worth naming rather than a state that silently passes.
- The Sourcery 150000-char refusal is a size limit the epic can predict; a diff over the limit is knowable before the barrier runs.

## Why it is routed here

This is the merge-gate semantics of the review apparatus itself.
