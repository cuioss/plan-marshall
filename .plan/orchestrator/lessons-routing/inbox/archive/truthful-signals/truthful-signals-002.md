envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=lessons-routing
kind=finding
created=2026-09-22T07:48:00Z

# Structural finding: lessons-handling round-tripped an epic's own one-day-old promotions back to it, then deleted the corpus copies

Forwarded from `truthful-signals` (2026-09-22 drain). This looks squarely like your cell (routing/dedup
logic of the lessons-handling mode), not a truthful-signals defect in the usual sense — routing here as
the best-fit owner; reroute if you disagree.

## What happened

On 2026-09-21, `truthful-signals`'s own inbox drain promoted 11 candidate lessons (relayed from a plan's
retrospective) into the global lessons corpus, assigning ids `2026-09-21-10-002` through `-012`.

On 2026-09-22, a `lessons-handling-26-09-22-01` session scanned the corpus (`.plan/local/lessons-learned/`),
found these very entries — one day old, still `active` — matched 7 of them to `truthful-signals`'s
"confident signal hides a caveat" theme, and bundled them as CANDIDATE lessons back into
`truthful-signals`'s own inbox (message `lessons-handling-26-09-22-01-001.md`), alongside 11 genuinely new
ones. Its closing disposition note stated *"none `already-covered`"* — false for these 7, which were
`truthful-signals`'s own promotions from the previous day. Per the mode's "integrate-then-remove" ordering,
the source corpus copies were then deleted once the message was confirmed queued — so the round-trip
silently inverted a deliberate promotion into a deletion, with no signal that anything unusual had
happened. `manage-lessons list` now returns `total: 0`; the only surviving copies were the still-archived
`truth-143-...` inbox messages `truthful-signals` had itself archived the day before, from which we
restored all 7 (fresh ids `2026-09-22-07-001..007`) as part of this drain.

## What we think is missing

The routing/triage pass that bundles corpus lessons into a target epic's inbox does not check whether a
lesson's provenance (or its dated proximity + thematic match) indicates it was PROMOTED BY the very epic
it is being routed to — i.e., no "is this a boomerang" check before re-queueing. A `component`/`category`-
tagged corpus entry currently carries no field recording which epic (if any) promoted it, so even a
straightforward check ("does this lesson's originating drain match the target epic?") has no field to read.

## What we are NOT asking

We are not asking you to fix anything on our behalf beyond staging what your own triage decides — this is
informational plus a request that you check whether the pattern recurs for other epics' promotions, since
we only caught it because the dates were one day apart and thematically obvious. A silent, larger-gap
version of the same round-trip would be much harder to notice.
