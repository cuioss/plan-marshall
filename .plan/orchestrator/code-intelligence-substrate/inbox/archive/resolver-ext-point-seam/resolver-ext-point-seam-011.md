envelope_version=1
sender_type=plan
sender_id=resolver-ext-point-seam
epic=code-intelligence-substrate
kind=finding
created=2026-07-30T15:21:25Z

## Finding — CORRECTION to message resolver-ext-point-seam-004: CodeRabbit did review PR #1067

**Type**: correction to a prior message from this same sender
**Supersedes**: `resolver-ext-point-seam-004.md` (written 2026-07-30T11:51:28Z)
**Status**: informational — no action needed on #1067 itself; the two tooling
dispositions message 004 proposed remain open and are now better-founded.

## Why this correction exists

Message 004 was written at 11:51. Its central factual claim was true at that moment and
false by 13:40. Draining 004 without this correction would seed the epic's ledger with a
review-coverage picture that the plan's own later history refutes.

## What message 004 got wrong

**1. CodeRabbit did review the diff.**

Message 004's table records coderabbit as `refused_awaitable` / "saw the diff: **no**". At
13:40:11Z CodeRabbit reviewed commit `371854d14` and filed 5 actionable inline comments
plus a review body. All 6 are in the plan's `pr-comment` findings store. They were rated:

| Finding | Severity | Substance |
|---|---|---|
| `8da924` | Major | resolver ids not validated or de-duplicated — mixed `str`/`int` sort can abort every graph query; two resolvers sharing an id collapse into one producer |
| `3e04a8` | Major | `merge_resolver_edges()` drops edges with no `notes[]` — a vacuous confident zero |
| `4a4012` | Major | `discover_derivation_resolvers()` outside the `ImportError` guard — documented zero-resolver fallback does not hold |
| `835226` | Minor | stale extension-point count ("one of those nine" vs eleven) |
| `4f670e` | Minor | hardcoded live-resolver counts in two docs |

All 5 became TASK-010..014, were fixed, and were re-verified. Message 004's own suggested
disposition — "schedule a post-merge revisit; coderabbit's window will have reopened" —
was in effect satisfied **during** the run.

**2. Sourcery's refusal was not a quota.**

Message 004 records `refused_hard` / `hard_quota`. `decision.log` at both 12:37:07 and
14:30:36 records the actual cause: a **150000-diff-character size cap, explicitly not a
quota**. This matters because the remediations are opposite — a quota clears by waiting, a
size cap never does. See candidate-lesson `resolver-ext-point-seam-006`.

## What message 004 got right, and what got worse

Its core thesis stands and is in fact **strengthened**: the final merged HEAD
`76c7200b6` was reviewed by **zero of three** configured bots.

- pr-agent (the **required** bot) reviewed only `405b05f06`, and only with an
  informational "PR Reviewer Guide" summary containing no actionable content. It never
  re-reviewed the merged HEAD.
- coderabbit reviewed `371854d14` — the HEAD *before* the 5 fixes it requested. It never
  saw the fixes.
- sourcery never reviewed any revision.

So the corrected picture is not "coverage was better than we thought". It is: **coverage
existed, arrived late, arrived by accident, and did not extend to what was merged.**

## The mechanism that made 004 wrong is itself the finding

Message 004 was generated from the same 11:51 snapshot as `review-retrospective.md`, and
that artifact was never regenerated after the 13:49 loop-back. Both inherited a
point-in-time reading of live bot state instead of querying the append-only `pr-comment`
findings ledger, which cannot go stale. See candidate-lesson
`resolver-ext-point-seam-005`.

## Suggested disposition

- Drain 004 and this correction **together**; do not act on 004's factual table alone.
- 004's two tooling proposals (`refused_awaitable` should engage
  `review_rate_window_await`; a partially-reviewed PR should not present the same
  `display_detail` shape as a fully-reviewed one) remain open and are now better evidenced
  — waiting *would* have worked for coderabbit, and demonstrably did once a rebase forced
  the retry.
- Add the third disposition 004 could not know to propose: **a required bot's review of an
  earlier HEAD should not satisfy the barrier at the merged HEAD.** See candidate-lesson
  `resolver-ext-point-seam-007`.
