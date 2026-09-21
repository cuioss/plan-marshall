envelope_version=1
sender_type=plan
sender_id=participation-credit-anchored-to-merge-candidate
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T21:25:37Z

component=plan-marshall:workflow-integration-github
category=bug
confidence=high
source_plan=participation-credit-anchored-to-merge-candidate
source_pr=1349

# A docstring promised three guards, the body implemented two, and the missing one silently inverted a time comparison

## Not covered by any existing message in this inbox

Messages -001 through -006 cover footprint persistence, merge-lock FIFO test vacuity,
cost measurement, finalize yield points, reviewer comparison, and the domain detector.
None of them touches finding `5de248`. This is a distinct defect with a distinct mechanism.

## Context

`github_pr._comment_predates_commit` is the ordering predicate the currency test uses to
decide whether a review comment precedes the commit being merged — i.e. whether a bot's
comment is stale relative to the merge candidate. Its docstring enumerated **three**
conditions under which it returns `False`:

> an unreadable commit timestamp, an absent comment timestamp, **or timestamps that do not compare**

The body implemented the first two. The third had no guard at all. The return was a bare
lexicographic string comparison:

```
latest < merge_candidate_committed_at
```

A `<` between two strings is **total** — it always yields a verdict. It can never signal
incomparability. So the promised third `False` was unreachable by construction.

## Why the gap is not merely undecided — it inverts

This is the part that makes it a defect rather than a documentation nit. Lexicographic
comparison of ISO-8601 timestamps is only order-preserving when every stamp shares one
shape. Mix offsets and it silently reverses:

- A stamp carrying a `-05:00` offset and a stamp carrying a `Z` suffix are compared
  character by character, so the ordering is decided by the **wall-clock digits**, not by
  the instant.
- A `-05:00` stamp therefore sorts BEFORE a `Z` stamp whenever its literal digits are
  smaller — while the instant it denotes is up to five hours LATER.

The predicate then reports "this comment predates the commit" about a comment that
**post-dates** it. And the direction of the error is the dangerous one: the arm this
feeds is the arm that errs toward crediting participation. The function's sibling
docstring states the rule it broke outright — "an unreadable timestamp must not become an
ordering claim" — and a total comparison over incomparable inputs is precisely an
unreadable timestamp becoming an ordering claim.

There is a second, quieter instance in the same function: `max()` was selecting the latest
comment stamp across mixed shapes, so the selection itself could pick the wrong comment
before any comparison happened.

## Root cause

Two things had to be true together:

1. **A stated safeguard with no code.** The docstring is where a maintainer, a reviewer,
   and a later caller all go to learn the contract. All three would have concluded the
   guard existed. The finding names the asymmetry exactly: "a stated safeguard with no code
   is the more expensive of the two errors here."
2. **A total operator standing in for a partial one.** `<` on strings never refuses, so
   there is no failure signal to notice — no exception, no `None`, no sentinel. The absent
   guard produces a confident wrong answer rather than an error, which is the same
   absent-is-not-false shape this plan existed to close, arriving through a comparison
   operator instead of through a schema field.

## How it was fixed (worth carrying — the fix chose the harder correct branch)

The finding offered two exits: implement the guard, or delete the third clause from the
docstring. The run implemented the guard. A module constant `_ISO_UTC_TIMESTAMP` pins the
single comparable shape (fixed-width ISO-8601 UTC with trailing `Z`, which is what `gh`
`committedDate` and comment timestamps actually emit); the commit stamp and **both**
comment stamps are matched against it before any ordering, and any non-match returns
`False`. Guarding the comment's own two stamps also closed the `max()` instance.

The verification is the part worth copying. Eight pinning tests were added: five
parametrized uncomparable shapes, one uncomparable commit stamp, plus a **matched positive
and negative control**. The pre-fix run is recorded verbatim — `6 failed, 18392 passed,
9 skipped` with all six named FAILED lines being the new guard cases, and **the two
controls passing pre-fix**. That is what proves the guard did not neuter the predicate:
without the controls, six new tests going red-to-green would be equally consistent with a
guard that now refuses everything.

## Proposed action

1. **Treat "docstring enumerates N conditions" as a checkable claim.** Each enumerated
   `False` condition should have a reachable branch. This one was catchable by reading the
   docstring against the body with nothing else in view — no cross-file context needed —
   which is why it belongs in the in-house structural gate's candidate surface as a first
   class check, not as an incidental catch.
2. **Sweep for other bare lexicographic timestamp/version comparisons.** The defect is not
   specific to this function; any `<`/`>`/`max()`/`sorted()` over externally-sourced
   ISO-8601 strings has it. `_ISO_UTC_TIMESTAMP` is now the repo's answer — the question is
   how many other sites still compare raw.
3. **Keep the matched-control discipline as the standard for guard fixes.** The pre-fix
   verbatim output plus a passing control is what distinguishes "the guard fires on the
   right inputs" from "the guard fires on everything".

## Evidence

- finding `5de248` (qgate 6-finalize, `bug`, `warning`, resolved `fixed`) at
  `workflow-integration-github/scripts/github_pr.py:792` — full docstring-vs-body analysis
  quoted above.
- resolution detail of `5de248` — `_ISO_UTC_TIMESTAMP`, the three guarded stamps, the 8
  pinning tests, and the verbatim pre-fix `6 failed, 18392 passed, 9 skipped in 228.59s`
  against post-fix `18398 passed, 0 failed`.
- sibling contract: the same file's docstring rule "an unreadable timestamp must not become
  an ordering claim".
- surfacing agent: `pre-submission-self-review` round 1 (`outcome: failed`, 5 defects); the
  external reviewer set produced 0 findings on the same diff.
