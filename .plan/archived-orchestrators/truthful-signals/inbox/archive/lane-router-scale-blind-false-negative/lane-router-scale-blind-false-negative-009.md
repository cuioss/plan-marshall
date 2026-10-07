envelope_version=1
sender_type=plan
sender_id=lane-router-scale-blind-false-negative
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T18:50:11Z

component=plan-marshall:workflow-integration-git
category=improvement
bundle=plan-marshall

# A rebase WIDENS a rename's population — re-derive the sweep after conflict resolution, never assume the original file list still bounds it

This plan carried an `auto` -> `standard` rename across 48 files. Mid-finalize it rebased
onto main and collided with **PR #1066 across 12 files**. Two things came out of the
resolution that are not obvious in advance:

**1. Neither wholesale resolution was correct.**

- Taking **upstream wholesale** left `auto` stranded against a renamed `LANE_TIERS` — a
  dangling reference to a symbol that no longer had that name.
- Taking **ours wholesale** would have **REVERTED #1066's operator-override fix** —
  silently deleting a shipped behaviour change from main.

The resolution rule that worked, stated as a rule: **upstream semantics win; our rename
re-applies on top.** Resolve to upstream's *behaviour*, then re-perform the mechanical
transformation against that behaviour. A rename is a transformation, not a set of file
contents, so it must be re-applied rather than re-selected.

**2. The rebase reintroduced the renamed vocabulary into files the original sweep never
touched.** Tier vocabulary reappeared in **three files** that were not in the 48-file
population, because upstream had added it there while the branch was in flight. The
original file list was a correct bound *at the time it was taken* and a wrong bound
afterward.

## Solution

After any rebase that touches a rename's surface:

- **Re-run the content sweep** that derived the original population. Do not diff against
  the original file list — the list is stale by construction, since upstream may have
  introduced new occurrences anywhere.
- Resolve conflicts by **upstream-semantics-win + re-apply-our-transformation**, per
  file, never by wholesale ours/theirs on a rename.
- Treat the count of renamed files as invalidated by the rebase, and re-derive it before
  stating any coverage claim about the rename.

## Impact

Applies to every mechanical wide transformation (renames, retired-token sweeps, API
migrations) that survives long enough to need a rebase. The "population is stale after
rebase" point is the one most likely to be missed, because the conflict list looks like
a complete report of what upstream changed — it is only a report of where upstream
changed *the same lines*.
