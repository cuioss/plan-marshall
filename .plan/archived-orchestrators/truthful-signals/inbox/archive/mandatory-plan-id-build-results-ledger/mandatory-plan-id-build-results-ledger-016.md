envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T21:28:39Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
title=Count-prose is a floor, and fixing it partially is the same defect

# Count-prose is a floor, and fixing it partially is the same defect

A documented count ("3 sites", "12 skills", "10 bundles with 149 components") is a
**floor**, not a fact — and a *partial* correction of stale count-prose is not a partial
fix, it is **the same defect in a new place**. The document still asserts a wrong number
with full confidence; only which number is wrong has changed.

## Recurrence

In `mandatory-plan-id-build-results-ledger` (`PLAN-TRUTH-026`, PR #1075), the ADR-002
count fix corrected **3 sites** and **missed 5 more in the same file**. The miss was caught
only by the `pre-submission-self-review` step — not by the author, not by the build, not
by any reviewer.

The "same file" detail is what makes this a distinct lesson rather than an instance of
generic staleness: the author had the file open, was actively fixing this exact class of
error in it, and still left 5 instances behind. **Being in the right file is not
proximity enough.**

## Why partial is as bad as none

- A document with 3 corrected and 5 stale counts reads as *freshly maintained*. The
  corrections are evidence of care, and that evidence is now misleading.
- The next reader has no way to tell which counts were reviewed. A wholly-stale document
  is at least uniformly untrustworthy; a partially-fixed one invites selective trust.
- Any detector keyed on "has this file been touched recently" now reports clean.

## Do this instead

- When you fix one count in a file, **enumerate every count-shaped claim in that file
  mechanically** before you finish — not by reading, by matching. A count you fixed is
  strong evidence that more exist nearby, because count-prose clusters.
- Treat the count you were asked to fix as the **discovery signal**, not the work item.
  The work item is the file's whole population of count claims.
- Re-derive each count from the authoritative set rather than adjusting the old number by
  the delta you happen to know about.
- Where a count must appear in prose, prefer a form that degrades safely (`over N`,
  `at least N`) or make it generated — a hand-maintained exact count is a standing
  liability.

## Related

- The **index-completeness** rule (a newly-authored index/summary table must enumerate
  every member of the set it indexes) is the same obligation seen from the table side: a
  count claim and an index table are two faces of "describe the set accurately".
- The `ext-self-review-plan-marshall` **stale count-prose** detector is what caught this;
  the lesson is evidence that the detector is load-bearing and should not be treated as
  advisory.
