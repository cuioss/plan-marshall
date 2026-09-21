envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T06:10:48Z

component=plan-marshall:phase-6-finalize
category=bug

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, PLAN-02
(`inherited-build-config-verification-depth`, merged as PR #714 / `7482cf18`).
bundle=plan-marshall

# review_commitments reconcile anchors on line numbers, which decay as the file grows

## Observation

A one-line grammar fix at `AGENTS.md:30` was flagged by the `review_commitments`
reconcile as conflicting with finding `5b36a3`, on the grounds that the finding's
recorded anchor was line 30.

That anchor was line 30 in the **round-1** file layout. By the time the reconcile
ran, the file had grown by roughly 20 lines and the finding's actual subject had
moved to lines 39-45 — untouched by the grammar fix. The two "line 30"s named
different text.

Acting on the flag would have reverted the grammar fix, restoring a comma splice
in order to protect prose that was never at risk. Recorded instead as finding
`0c3b51`, resolved `taken_into_account`.

## The generalisable rule

A bare line number is not a stable identity for a finding's subject inside a file
that is still being edited. Any reconcile that compares a later edit against an
earlier finding by line number alone will produce false positives in exact
proportion to how much the file grew between them — and the false positive
argues for *reverting correct work*, which is the expensive direction to be
wrong in.

## Suggested corrective action

Anchor a review commitment on content rather than position: the quoted subject
text, a content hash of the enclosing hunk, or a re-derived match at reconcile
time. Where a line number must be kept, re-anchor it against the current file
before comparing (the same way a stale diff hunk is re-applied), and treat a
failed re-anchor as `indeterminate` rather than as a conflict.

## Impact

The louder the review loop (more rounds, more growth between rounds), the more
false conflicts this produces — and it produces them exactly when the plan is
under the most review pressure and least able to spend time refuting them.
