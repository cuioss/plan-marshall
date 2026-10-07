envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:34:58Z

component=plan-marshall:automatic-review
category=bug
confidence=high
source_plan=runtime-edge-paths-crash-or-silently-lose-data
source_finding=a8d263
source_signal=automated_review
likely_epic=review-apparatus

# Bot participation flipped from proven to unproven at an unchanged HEAD

## Context

On PR #1132 the same bot was classified two different ways by two fetches of the same PR at the
same HEAD, roughly 24 minutes apart:

- **18:41** — the `automatic-review` FIND step reported `participated_bots: pr-agent:issue_comment`
  and the participation predicate returned `participation_complete: true`.
- **~19:05** — the pre-merge barrier re-fetched the SAME PR at the SAME HEAD `cbb184c9d` and
  returned `participated_bots` **empty**, with `stale_participation_bots: pr-agent:issue_comment`.
  The predicate flipped to `participation_complete: false`, `pr-agent=participated_stale`.

Nothing about the tree changed in the interval. `branch-sync-state` reported synced at `cbb184c9d`,
the pre-merge rebase was `action: noop` with `pre_sha == post_sha`, and no push occurred.

## Root cause (to be determined — this is the actionable question)

The `participation_requires_update` currency test is **not a pure function of
`(bot, comment, HEAD)`**. Some time-varying input moves it, and the observed direction of movement
is from proven to unproven. Candidates worth checking before either verdict is treated as
authoritative: a wall-clock freshness window on the comment, a comparison against a mutable PR
field such as `updatedAt` rather than the commit SHA, or a paging/ordering effect in the comment
fetch.

## Why the direction matters

**The earlier `true` is the dangerous reading**, because that is the one a merge would have
proceeded on. A step that marks itself `done` on a participation verdict can be contradicted by a
later re-derivation of the same verdict with no intervening change. That the barrier re-derives
rather than trusting the recorded verdict is the design working correctly — this run is evidence
*for* the barrier, not against it.

But it is also a signal that "a bot participated" is currently a claim with an unstated time
dependency, and the epic's whole subject is claims that read as settled facts while carrying an
unstated caveat.

## Proposed action

1. Establish what `participation_requires_update` actually compares, and pin it with a test that
   asserts the verdict is stable across two evaluations at an unchanged HEAD.
2. Until it is pure, have the predicate report **which input it keyed on** alongside the verdict, so
   a `participated` and a later `participated_stale` for the same `(bot, HEAD)` are reconcilable
   rather than simply contradictory.
3. Treat a proven-to-unproven flip at an unchanged HEAD as a reportable anomaly rather than a
   silent re-classification.

## Evidence

- finding `a8d263` (this plan), severity warning, component `plan-marshall:automatic-review`
- `status.metadata.merge_authorizations['barrier-ask-override']` — the override this contradiction
  forced, granted at `2026-08-09T19:39:45Z` over `participation_complete=false`, whose recorded
  `reason` names this finding explicitly
- the two verdicts are both on record in the plan's finalize log at 18:41 and ~19:05

## Routing note

This is a review-bot / PR-review observation, so it most likely belongs to the **`review-apparatus`**
epic rather than to `truthful-signals`. Per the inbox contract the plan performs no epic
classification — flagging the likely destination as a lead for the drain, not as a decision.
